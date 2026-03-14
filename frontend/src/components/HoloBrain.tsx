import { useRef, useMemo, useCallback } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
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

/* ─── Anatomical brain shape: surface-only distribution ─── */
function generateBrainNodes(count: number): Float32Array {
  const positions = new Float32Array(count * 3)

  for (let i = 0; i < count; i++) {
    const r1 = hash(i, 1)
    const r2 = hash(i, 2)
    const r3 = hash(i, 3)
    const r4 = hash(i, 4)

    // Spherical coordinates
    const theta = r1 * Math.PI * 2
    const phi = Math.acos(2 * r2 - 1)

    // Base sphere direction
    const sx = Math.sin(phi) * Math.cos(theta)
    const sy = Math.sin(phi) * Math.sin(theta)
    const sz = Math.cos(phi)

    // ── Brain-specific deformations ──

    // 1. Elongate front-to-back (Z axis) and flatten top-to-bottom (Y axis slightly)
    let x = sx * 0.82
    let y = sy * 0.72
    let z = sz * 0.92

    // 2. Widen at the top (parietal), narrow at the bottom (brainstem area)
    const verticalFactor = y > 0 ? 1.0 + y * 0.15 : 1.0 - Math.abs(y) * 0.3
    x *= verticalFactor
    z *= verticalFactor

    // 3. Frontal lobe bulge (front = positive Z)
    if (z > 0.2) {
      const frontalBulge = Math.pow((z - 0.2) / 0.72, 2) * 0.12
      x *= 1.0 + frontalBulge
      y *= 1.0 + frontalBulge * 0.5
    }

    // 4. Temporal lobe widening (sides at mid-low height)
    if (y < 0.1 && y > -0.5) {
      const temporalFactor = (1.0 - Math.abs(y + 0.2) / 0.3) * 0.15
      x *= 1.0 + Math.max(0, temporalFactor)
    }

    // 5. Occipital bulge (back = negative Z)
    if (z < -0.3) {
      const occipitalBulge = Math.pow((-z - 0.3) / 0.62, 2) * 0.08
      x *= 1.0 + occipitalBulge * 0.5
      y *= 1.0 + occipitalBulge
    }

    // 6. Longitudinal fissure (gap between hemispheres at top)
    const fissureDepth = y > 0 ? 0.06 + y * 0.04 : 0.03
    if (Math.abs(x) < fissureDepth) {
      x += (x >= 0 ? 1 : -1) * (fissureDepth - Math.abs(x) + 0.02)
    }

    // 7. Flatten bottom (base of brain)
    if (y < -0.55) {
      y = -0.55 - (y + 0.55) * 0.2
    }

    // 8. Surface noise for sulci/gyri (cortical folds)
    const freq1 = 6.0, freq2 = 12.0
    const sulci =
      Math.sin(x * freq1 + z * freq1 * 1.3) * 0.025 +
      Math.sin(y * freq2 + x * freq2 * 0.8) * 0.015 +
      Math.cos(z * freq1 * 1.7 + y * freq1) * 0.02

    // Apply noise along the surface normal (radial direction)
    const len = Math.sqrt(x * x + y * y + z * z) || 1
    x += (x / len) * sulci
    y += (y / len) * sulci * 0.7
    z += (z / len) * sulci

    // 9. Slight random surface displacement for organic feel
    const disp = (r3 - 0.5) * 0.025 + (r4 - 0.5) * 0.015
    x += (x / len) * disp
    y += (y / len) * disp
    z += (z / len) * disp

    positions[i * 3] = x
    positions[i * 3 + 1] = y
    positions[i * 3 + 2] = z
  }

  return positions
}

/* ─── Connection lines between nearby nodes ─── */
function generateConnections(
  positions: Float32Array,
  nodeCount: number,
  maxDistance: number,
  maxConn: number,
): Float32Array {
  const lines: number[] = []
  const connCount = new Uint8Array(nodeCount)

  for (let i = 0; i < nodeCount; i++) {
    if (connCount[i] >= maxConn) continue
    const ix = positions[i * 3], iy = positions[i * 3 + 1], iz = positions[i * 3 + 2]

    for (let j = i + 1; j < nodeCount; j++) {
      if (connCount[j] >= maxConn) continue
      const dx = positions[j * 3] - ix
      const dy = positions[j * 3 + 1] - iy
      const dz = positions[j * 3 + 2] - iz
      const dist = dx * dx + dy * dy + dz * dz // squared distance

      if (dist < maxDistance * maxDistance) {
        // Don't connect across the fissure (both must be same hemisphere)
        if (ix * positions[j * 3] < -0.001) continue

        lines.push(ix, iy, iz, positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2])
        connCount[i]++
        connCount[j]++
      }
    }
  }

  return new Float32Array(lines)
}

const NODE_COUNT = 650

/* ─── Neural nodes (points) ─── */
function BrainNodes({ state }: { state: BrainState }) {
  const pointsRef = useRef<THREE.Points>(null)

  const { positions, baseSizes, phases } = useMemo(() => {
    const pos = generateBrainNodes(NODE_COUNT)
    const sz = new Float32Array(NODE_COUNT)
    const ph = new Float32Array(NODE_COUNT)
    for (let i = 0; i < NODE_COUNT; i++) {
      sz[i] = 0.012 + hash(i, 10) * 0.022
      ph[i] = hash(i, 20) * Math.PI * 2
    }
    return { positions: pos, baseSizes: sz, phases: ph }
  }, [])

  const liveSizes = useMemo(() => new Float32Array(baseSizes), [baseSizes])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const t = clock.getElapsedTime()
    const geo = pointsRef.current.geometry
    const sizeAttr = geo.getAttribute('size') as THREE.BufferAttribute

    const pulseSpeed = state === 'thinking' ? 4 : state === 'responding' ? 2.5 : 1
    const pulseAmp = state === 'thinking' ? 0.018 : state === 'responding' ? 0.012 : 0.006

    for (let i = 0; i < NODE_COUNT; i++) {
      liveSizes[i] = baseSizes[i] + Math.sin(t * pulseSpeed + phases[i]) * pulseAmp
    }
    sizeAttr.array = liveSizes
    sizeAttr.needsUpdate = true

    const rotSpeed = state === 'thinking' ? 0.15 : state === 'responding' ? 0.1 : 0.03
    pointsRef.current.rotation.y += rotSpeed * 0.016
    pointsRef.current.rotation.x = Math.sin(t * 0.2) * 0.04
  })

  const color = state === 'thinking' ? '#00F0FF'
    : state === 'responding' ? '#40F8FF'
    : state === 'activating' ? '#FFFFFF'
    : state === 'typing' ? '#60D0E0'
    : '#00C8D8'

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[new Float32Array(baseSizes), 1]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.028}
        color={color}
        transparent
        opacity={state === 'idle' ? 0.7 : 0.95}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

/* ─── Synaptic connections (lines) ─── */
function BrainConnections({ state }: { state: BrainState }) {
  const linesRef = useRef<THREE.LineSegments>(null)

  const linePositions = useMemo(() => {
    const positions = generateBrainNodes(NODE_COUNT)
    return generateConnections(positions, NODE_COUNT, 0.22, 4)
  }, [])

  useFrame(({ clock }) => {
    if (!linesRef.current) return
    const t = clock.getElapsedTime()
    const rotSpeed = state === 'thinking' ? 0.15 : state === 'responding' ? 0.1 : 0.03
    linesRef.current.rotation.y += rotSpeed * 0.016
    linesRef.current.rotation.x = Math.sin(t * 0.2) * 0.04

    const mat = linesRef.current.material as THREE.LineBasicMaterial
    const baseOp = state === 'thinking' ? 0.3 : state === 'responding' ? 0.22 : 0.1
    mat.opacity = baseOp + Math.sin(t * 2) * 0.04
  })

  const color = state === 'thinking' ? '#00F0FF' : state === 'responding' ? '#30D0E0' : '#007888'

  return (
    <lineSegments ref={linesRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={0.12}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  )
}

/* ─── Scan line — thin glowing ring that sweeps through the brain ─── */
function ScanRing({ state }: { state: BrainState }) {
  const ringRef = useRef<THREE.LineLoop>(null)

  const ringPositions = useMemo(() => {
    const segments = 128
    const arr = new Float32Array(segments * 3)
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      arr[i * 3] = Math.cos(angle) * 0.95
      arr[i * 3 + 1] = 0
      arr[i * 3 + 2] = Math.sin(angle) * 0.85
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const t = clock.getElapsedTime()
    const speed = state === 'thinking' ? 1.5 : 0.5
    ringRef.current.position.y = Math.sin(t * speed) * 0.65

    const mat = ringRef.current.material as THREE.LineBasicMaterial
    mat.opacity = state === 'idle' ? 0.06 : state === 'thinking' ? 0.25 : 0.12
  })

  return (
    <lineLoop ref={ringRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[ringPositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color="#00F0FF"
        transparent
        opacity={0.1}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineLoop>
  )
}

/* ─── Ambient particles ─── */
function AmbientParticles() {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const arr = new Float32Array(80 * 3)
    for (let i = 0; i < 80; i++) {
      arr[i * 3] = (hash(i, 50) - 0.5) * 5
      arr[i * 3 + 1] = (hash(i, 51) - 0.5) * 5
      arr[i * 3 + 2] = (hash(i, 52) - 0.5) * 5
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.008
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.006}
        color="#00F0FF"
        transparent
        opacity={0.15}
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
      <ambientLight intensity={0.08} />
      <pointLight position={[3, 3, 3]} intensity={0.25} color="#00F0FF" />
      <pointLight position={[-3, -2, 3]} intensity={0.12} color="#00F0FF" />
      <BrainNodes state={state} />
      <BrainConnections state={state} />
      <ScanRing state={state} />
      <AmbientParticles />
      <EffectComposer>
        <Bloom
          luminanceThreshold={0.15}
          luminanceSmoothing={0.9}
          intensity={state === 'thinking' ? 2.2 : state === 'responding' ? 1.6 : 0.9}
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
        camera={{ position: [0, 0.1, 2.4], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        style={{ background: 'transparent' }}
      >
        <BrainScene state={state} />
      </Canvas>
    </div>
  )
}
