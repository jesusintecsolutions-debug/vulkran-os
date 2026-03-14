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

/* ─── Procedural brain node positions ─── */
function generateBrainNodes(count: number): Float32Array {
  const positions = new Float32Array(count * 3)
  const seed = 42

  for (let i = 0; i < count; i++) {
    const t1 = Math.sin(i * 127.1 + seed) * 43758.5453
    const t2 = Math.sin(i * 269.5 + seed) * 43758.5453
    const t3 = Math.sin(i * 419.2 + seed) * 43758.5453
    const r1 = t1 - Math.floor(t1)
    const r2 = t2 - Math.floor(t2)
    const r3 = t3 - Math.floor(t3)

    const theta = r1 * Math.PI * 2
    const phi = Math.acos(2 * r2 - 1)
    const radius = 0.7 + r3 * 0.35

    let x = radius * Math.sin(phi) * Math.cos(theta)
    const y = radius * Math.sin(phi) * Math.sin(theta) * 0.85
    const z = radius * Math.cos(phi) * 0.9

    // Brain fissure gap
    if (Math.abs(x) < 0.04) x += (x >= 0 ? 1 : -1) * 0.06

    // Surface noise (sulci/gyri)
    const noise = Math.sin(x * 8 + y * 6) * 0.04 + Math.cos(y * 10 + z * 7) * 0.03
    positions[i * 3] = x + noise
    positions[i * 3 + 1] = y + noise * 0.7
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
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)

      if (dist < maxDistance) {
        lines.push(ix, iy, iz, positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2])
        connCount[i]++
        connCount[j]++
      }
    }
  }

  return new Float32Array(lines)
}

const NODE_COUNT = 280

/* ─── Neural nodes (points) ─── */
function BrainNodes({ state }: { state: BrainState }) {
  const pointsRef = useRef<THREE.Points>(null)

  const { positions, baseSizes, phases } = useMemo(() => {
    const pos = generateBrainNodes(NODE_COUNT)
    const sz = new Float32Array(NODE_COUNT)
    const ph = new Float32Array(NODE_COUNT)
    for (let i = 0; i < NODE_COUNT; i++) {
      sz[i] = 0.015 + Math.random() * 0.025
      ph[i] = Math.random() * Math.PI * 2
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
    const pulseAmp = state === 'thinking' ? 0.02 : state === 'responding' ? 0.015 : 0.008

    for (let i = 0; i < NODE_COUNT; i++) {
      liveSizes[i] = baseSizes[i] + Math.sin(t * pulseSpeed + phases[i]) * pulseAmp
    }
    sizeAttr.array = liveSizes
    sizeAttr.needsUpdate = true

    const rotSpeed = state === 'thinking' ? 0.15 : state === 'responding' ? 0.1 : 0.03
    pointsRef.current.rotation.y += rotSpeed * 0.016
    pointsRef.current.rotation.x = Math.sin(t * 0.2) * 0.05
  })

  const color = state === 'thinking' ? '#00F0FF'
    : state === 'responding' ? '#40F8FF'
    : state === 'activating' ? '#FFFFFF'
    : state === 'typing' ? '#60D0E0'
    : '#00C0D0'

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[new Float32Array(baseSizes), 1]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.035}
        color={color}
        transparent
        opacity={state === 'idle' ? 0.6 : 0.9}
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
    return generateConnections(positions, NODE_COUNT, 0.28, 3)
  }, [])

  useFrame(({ clock }) => {
    if (!linesRef.current) return
    const t = clock.getElapsedTime()
    const rotSpeed = state === 'thinking' ? 0.15 : state === 'responding' ? 0.1 : 0.03
    linesRef.current.rotation.y += rotSpeed * 0.016
    linesRef.current.rotation.x = Math.sin(t * 0.2) * 0.05

    const mat = linesRef.current.material as THREE.LineBasicMaterial
    const baseOp = state === 'thinking' ? 0.25 : state === 'responding' ? 0.2 : 0.08
    mat.opacity = baseOp + Math.sin(t * 2) * 0.03
  })

  const color = state === 'thinking' ? '#00F0FF' : state === 'responding' ? '#30D0E0' : '#006878'

  return (
    <lineSegments ref={linesRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={0.1}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </lineSegments>
  )
}

/* ─── Scan line ring ─── */
function ScanRing({ state }: { state: BrainState }) {
  const ringRef = useRef<THREE.Mesh>(null)

  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const t = clock.getElapsedTime()
    const speed = state === 'thinking' ? 1.5 : 0.5
    ringRef.current.position.y = Math.sin(t * speed) * 0.8
    ringRef.current.rotation.x = Math.PI / 2

    const mat = ringRef.current.material as THREE.MeshBasicMaterial
    mat.opacity = state === 'idle' ? 0.03 : state === 'thinking' ? 0.12 : 0.06
  })

  return (
    <mesh ref={ringRef}>
      <ringGeometry args={[0.6, 1.2, 64]} />
      <meshBasicMaterial
        color="#00F0FF"
        transparent
        opacity={0.05}
        side={THREE.DoubleSide}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  )
}

/* ─── Ambient particles ─── */
function AmbientParticles() {
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const arr = new Float32Array(100 * 3)
    for (let i = 0; i < 100; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 4
      arr[i * 3 + 1] = (Math.random() - 0.5) * 4
      arr[i * 3 + 2] = (Math.random() - 0.5) * 4
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.01
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.008}
        color="#00F0FF"
        transparent
        opacity={0.2}
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
      <ambientLight intensity={0.1} />
      <pointLight position={[3, 3, 3]} intensity={0.3} color="#00F0FF" />
      <pointLight position={[-3, -2, 3]} intensity={0.15} color="#00F0FF" />
      <BrainNodes state={state} />
      <BrainConnections state={state} />
      <ScanRing state={state} />
      <AmbientParticles />
      <EffectComposer>
        <Bloom
          luminanceThreshold={0.2}
          luminanceSmoothing={0.9}
          intensity={state === 'thinking' ? 2.0 : state === 'responding' ? 1.5 : 0.8}
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
        camera={{ position: [0, 0, 2.5], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        style={{ background: 'transparent' }}
      >
        <BrainScene state={state} />
      </Canvas>
    </div>
  )
}
