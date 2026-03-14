import { useRef, useMemo, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

export type BrainState = 'idle' | 'typing' | 'thinking' | 'responding' | 'activating'

interface HoloBrainProps {
  state?: BrainState
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  onClick?: () => void
}

/* ─── Deterministic pseudo-random ─── */
function hash(i: number, seed: number): number {
  const t = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453
  return t - Math.floor(t)
}

/* ─── Brain surface point: returns [x, y, z] on an anatomical brain shape ─── */
function brainSurfacePoint(
  theta: number,
  phi: number,
  radiusJitter: number,
): [number, number, number] {
  // Base sphere
  const sx = Math.sin(phi) * Math.cos(theta)
  const sy = Math.sin(phi) * Math.sin(theta)
  const sz = Math.cos(phi)

  // Scale to brain proportions: wider (X), shorter (Y), elongated (Z)
  let x = sx * 0.85
  let y = sy * 0.68
  let z = sz * 0.95

  // Frontal lobe bulge
  if (z > 0.15) {
    const f = Math.pow((z - 0.15) / 0.8, 1.5) * 0.18
    x *= 1.0 + f
    y *= 1.0 + f * 0.6
  }

  // Temporal lobe widening (sides, lower half)
  if (y < 0.15 && y > -0.45) {
    const t = Math.max(0, 1.0 - Math.abs(y + 0.15) / 0.3) * 0.18
    x *= 1.0 + t
  }

  // Occipital lobe (back)
  if (z < -0.25) {
    const o = Math.pow((-z - 0.25) / 0.7, 1.5) * 0.1
    y *= 1.0 + o
  }

  // Parietal widening (top)
  if (y > 0.1) {
    x *= 1.0 + y * 0.12
    z *= 1.0 + y * 0.06
  }

  // Flatten bottom
  if (y < -0.5) y = -0.5 - (y + 0.5) * 0.15

  // Longitudinal fissure
  const fissureWidth = y > 0 ? 0.055 + y * 0.04 : 0.025
  if (Math.abs(x) < fissureWidth) {
    x += (x >= 0 ? 1 : -1) * (fissureWidth - Math.abs(x) + 0.015)
  }

  // Sulci/gyri surface detail
  const s1 = Math.sin(x * 7 + z * 9) * 0.022
  const s2 = Math.sin(y * 13 + x * 11) * 0.015
  const s3 = Math.cos(z * 8 + y * 7) * 0.018
  const sulci = s1 + s2 + s3

  const len = Math.sqrt(x * x + y * y + z * z) || 1
  const nx = x / len, ny = y / len, nz = z / len
  x += nx * (sulci + radiusJitter)
  y += ny * (sulci + radiusJitter) * 0.7
  z += nz * (sulci + radiusJitter)

  return [x, y, z]
}

/* ─── Generate dense brain particles ─── */
const SURFACE_COUNT = 3500
const INNER_COUNT = 800
const TOTAL = SURFACE_COUNT + INNER_COUNT

function generateBrainCloud(): { positions: Float32Array; depths: Float32Array } {
  const positions = new Float32Array(TOTAL * 3)
  const depths = new Float32Array(TOTAL) // 0=surface, 1=deep interior

  // Surface particles — dense shell
  for (let i = 0; i < SURFACE_COUNT; i++) {
    const theta = hash(i, 1) * Math.PI * 2
    const phi = Math.acos(2 * hash(i, 2) - 1)
    const jitter = (hash(i, 3) - 0.5) * 0.035

    const [x, y, z] = brainSurfacePoint(theta, phi, jitter)
    positions[i * 3] = x
    positions[i * 3 + 1] = y
    positions[i * 3 + 2] = z
    depths[i] = 0
  }

  // Inner volume particles — sparser, for depth/glow
  for (let i = 0; i < INNER_COUNT; i++) {
    const idx = SURFACE_COUNT + i
    const theta = hash(i, 10) * Math.PI * 2
    const phi = Math.acos(2 * hash(i, 11) - 1)
    const shrink = 0.3 + hash(i, 12) * 0.5 // 30%-80% of surface radius
    const jitter = (hash(i, 13) - 0.5) * 0.02

    const [sx, sy, sz] = brainSurfacePoint(theta, phi, jitter)
    positions[idx * 3] = sx * shrink
    positions[idx * 3 + 1] = sy * shrink
    positions[idx * 3 + 2] = sz * shrink
    depths[idx] = 1.0 - shrink
  }

  return { positions, depths }
}

/* ─── Brain particle cloud ─── */
function BrainCloud({ state }: { state: BrainState }) {
  const pointsRef = useRef<THREE.Points>(null)

  const { positions, colors, baseSizes, phases } = useMemo(() => {
    const { positions: pos, depths } = generateBrainCloud()

    // Color gradient: surface = bright cyan, interior = deeper teal/blue
    const col = new Float32Array(TOTAL * 3)
    const sz = new Float32Array(TOTAL)
    const ph = new Float32Array(TOTAL)

    for (let i = 0; i < TOTAL; i++) {
      const d = depths[i]
      const y = pos[i * 3 + 1]
      const x = pos[i * 3]

      // Height-based color variation: top = cyan, bottom = teal
      const heightFactor = (y + 0.7) / 1.4 // 0 at bottom, 1 at top
      const sideFactor = Math.abs(x) / 0.9 // 0 at center, 1 at sides

      // RGB: mix between cyan (#00F0FF) and teal (#008090) based on height + depth
      const r = d > 0.3 ? 0.0 : 0.0 + sideFactor * 0.05
      const g = d > 0.3
        ? 0.3 + heightFactor * 0.3
        : 0.7 + heightFactor * 0.25 + sideFactor * 0.05
      const b = d > 0.3
        ? 0.4 + heightFactor * 0.2
        : 0.85 + heightFactor * 0.15

      col[i * 3] = r
      col[i * 3 + 1] = g
      col[i * 3 + 2] = b

      // Size: surface = small dense, interior = larger glow
      sz[i] = d > 0.3
        ? 0.015 + hash(i, 30) * 0.02 // inner: larger
        : 0.006 + hash(i, 30) * 0.012 // surface: small and dense
      ph[i] = hash(i, 40) * Math.PI * 2
    }

    return { positions: pos, colors: col, baseSizes: sz, phases: ph }
  }, [])

  const liveSizes = useMemo(() => new Float32Array(baseSizes), [baseSizes])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const t = clock.getElapsedTime()
    const geo = pointsRef.current.geometry
    const sizeAttr = geo.getAttribute('size') as THREE.BufferAttribute

    const pulseSpeed = state === 'thinking' ? 5 : state === 'responding' ? 3 : 1.2
    const pulseAmp = state === 'thinking' ? 0.008 : state === 'responding' ? 0.005 : 0.002

    for (let i = 0; i < TOTAL; i++) {
      liveSizes[i] = baseSizes[i] + Math.sin(t * pulseSpeed + phases[i]) * pulseAmp
    }
    sizeAttr.array = liveSizes
    sizeAttr.needsUpdate = true

    // Slow auto-rotation (only when not dragging — OrbitControls handles drag)
    const autoSpeed = state === 'thinking' ? 0.08 : state === 'responding' ? 0.05 : 0.015
    pointsRef.current.rotation.y += autoSpeed * 0.016
  })

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        <bufferAttribute attach="attributes-size" args={[new Float32Array(baseSizes), 1]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.018}
        vertexColors
        transparent
        opacity={state === 'idle' ? 0.75 : 0.95}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

/* ─── Scan line — thin glowing ring ─── */
function ScanRing({ state }: { state: BrainState }) {
  const ringRef = useRef<THREE.LineLoop>(null)

  const ringPositions = useMemo(() => {
    const segments = 128
    const arr = new Float32Array(segments * 3)
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      arr[i * 3] = Math.cos(angle) * 0.92
      arr[i * 3 + 1] = 0
      arr[i * 3 + 2] = Math.sin(angle) * 0.88
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const t = clock.getElapsedTime()
    const speed = state === 'thinking' ? 1.8 : 0.5
    ringRef.current.position.y = Math.sin(t * speed) * 0.6

    const mat = ringRef.current.material as THREE.LineBasicMaterial
    mat.opacity = state === 'idle' ? 0.04 : state === 'thinking' ? 0.2 : 0.1
  })

  return (
    <lineLoop ref={ringRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[ringPositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color="#00F0FF"
        transparent
        opacity={0.08}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineLoop>
  )
}

/* ─── Ambient dust ─── */
function AmbientParticles() {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const arr = new Float32Array(60 * 3)
    for (let i = 0; i < 60; i++) {
      arr[i * 3] = (hash(i, 50) - 0.5) * 5
      arr[i * 3 + 1] = (hash(i, 51) - 0.5) * 5
      arr[i * 3 + 2] = (hash(i, 52) - 0.5) * 5
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.006
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.005}
        color="#00F0FF"
        transparent
        opacity={0.12}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

/* ─── Scene ─── */
function BrainScene({ state }: { state: BrainState }) {
  return (
    <>
      <ambientLight intensity={0.05} />
      <pointLight position={[2, 3, 2]} intensity={0.2} color="#00F0FF" />
      <pointLight position={[-2, -1, 3]} intensity={0.1} color="#008888" />
      <BrainCloud state={state} />
      <ScanRing state={state} />
      <AmbientParticles />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        rotateSpeed={0.5}
        dampingFactor={0.12}
        enableDamping
        minPolarAngle={Math.PI * 0.2}
        maxPolarAngle={Math.PI * 0.8}
      />
      <EffectComposer>
        <Bloom
          luminanceThreshold={0.1}
          luminanceSmoothing={0.9}
          intensity={state === 'thinking' ? 2.5 : state === 'responding' ? 1.8 : 1.0}
        />
      </EffectComposer>
    </>
  )
}

/* ─── Public component ─── */
export function HoloBrain({ state = 'idle', size = 'md', className, onClick }: HoloBrainProps) {
  const sizeMap = {
    sm: 'h-24 w-24',
    md: 'h-40 w-40',
    lg: 'h-56 w-56',
    xl: 'h-72 w-72 md:h-80 md:w-80',
  }

  const handleClick = useCallback(() => onClick?.(), [onClick])

  return (
    <div className={`${sizeMap[size]} ${className || ''} cursor-pointer`} onClick={handleClick}>
      <Canvas
        camera={{ position: [0, 0.15, 2.2], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        style={{ background: 'transparent' }}
      >
        <BrainScene state={state} />
      </Canvas>
    </div>
  )
}
