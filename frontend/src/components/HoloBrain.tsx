import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, MeshDistortMaterial } from '@react-three/drei'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'

type BrainState = 'idle' | 'typing' | 'thinking' | 'responding'

interface HoloBrainProps {
  state?: BrainState
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

/* ─── Core orb ─── */
function BrainOrb({ state }: { state: BrainState }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const glowRef = useRef<THREE.Mesh>(null)

  const config = useMemo(
    () => ({
      idle: { speed: 1.5, distort: 0.3, color: '#8B5CF6', emissive: '#4C1D95', scale: 1 },
      typing: { speed: 2.5, distort: 0.35, color: '#A78BFA', emissive: '#5B21B6', scale: 1.02 },
      thinking: { speed: 4, distort: 0.5, color: '#00F0FF', emissive: '#0891B2', scale: 1.05 },
      responding: { speed: 3, distort: 0.4, color: '#8B5CF6', emissive: '#6D28D9', scale: 1.08 },
    }),
    [],
  )

  const { speed, distort, color, emissive, scale } = config[state]

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.3
      meshRef.current.rotation.x = Math.sin(Date.now() * 0.001) * 0.1
      // Smooth scale transition
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), delta * 3)
    }
    if (glowRef.current) {
      glowRef.current.rotation.y -= delta * 0.2
      const pulse = state === 'thinking' ? 1 + Math.sin(Date.now() * 0.005) * 0.08 : 1
      glowRef.current.scale.setScalar(1.15 * pulse)
    }
  })

  return (
    <group>
      {/* Outer glow sphere */}
      <Sphere ref={glowRef} args={[1, 32, 32]}>
        <meshBasicMaterial color={color} transparent opacity={0.04} side={THREE.BackSide} />
      </Sphere>

      {/* Main orb */}
      <Sphere ref={meshRef} args={[1, 64, 64]}>
        <MeshDistortMaterial
          color={color}
          emissive={emissive}
          emissiveIntensity={0.6}
          roughness={0.2}
          metalness={0.8}
          distort={distort}
          speed={speed}
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* Particle ring */}
      <ParticleRing state={state} />
    </group>
  )
}

/* ─── Orbiting particles ─── */
function ParticleRing({ state }: { state: BrainState }) {
  const count = 60
  const ref = useRef<THREE.Points>(null)

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2
      const radius = 1.4 + Math.random() * 0.3
      arr[i * 3] = Math.cos(angle) * radius
      arr[i * 3 + 1] = (Math.random() - 0.5) * 0.6
      arr[i * 3 + 2] = Math.sin(angle) * radius
    }
    return arr
  }, [])

  useFrame((_, delta) => {
    if (ref.current) {
      const speed = state === 'thinking' ? 0.8 : state === 'responding' ? 0.5 : 0.2
      ref.current.rotation.y += delta * speed
      ref.current.rotation.x = Math.sin(Date.now() * 0.0005) * 0.15
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color={state === 'thinking' ? '#00F0FF' : '#A78BFA'}
        transparent
        opacity={0.7}
        sizeAttenuation
      />
    </points>
  )
}

/* ─── Canvas wrapper ─── */
export function HoloBrain({ state = 'idle', size = 'md', className }: HoloBrainProps) {
  const sizeMap = {
    sm: 'h-24 w-24',
    md: 'h-40 w-40',
    lg: 'h-56 w-56',
  }

  return (
    <div className={`${sizeMap[size]} ${className || ''}`}>
      <Canvas
        camera={{ position: [0, 0, 3], fov: 45 }}
        gl={{ alpha: true, antialias: true }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={0.8} color="#8B5CF6" />
        <pointLight position={[-5, -3, 5]} intensity={0.4} color="#00F0FF" />

        <BrainOrb state={state} />

        <EffectComposer>
          <Bloom
            luminanceThreshold={0.3}
            luminanceSmoothing={0.9}
            intensity={1.2}
          />
        </EffectComposer>
      </Canvas>
    </div>
  )
}
