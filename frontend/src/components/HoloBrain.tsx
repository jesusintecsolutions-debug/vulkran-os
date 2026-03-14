import { useRef, useMemo, Suspense } from 'react'
import { Canvas, useFrame, useLoader } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshSurfaceSampler } from 'three/examples/jsm/math/MeshSurfaceSampler.js'

export type BrainState = 'idle' | 'typing' | 'thinking' | 'responding' | 'activating'

interface HoloBrainProps {
  state?: BrainState
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
  onClick?: () => void
}

/* ─── Custom holographic shader ─── */
const holoVertexShader = /* glsl */ `
  attribute float aSize;
  attribute float aPhase;
  attribute float aDepth;
  attribute vec3 aColor;

  varying vec3 vColor;
  varying float vDepth;
  varying float vPhase;

  uniform float uTime;
  uniform float uPulseSpeed;
  uniform float uPulseAmp;

  void main() {
    vColor = aColor;
    vDepth = aDepth;
    vPhase = aPhase;

    float pulse = sin(uTime * uPulseSpeed + aPhase) * uPulseAmp;
    float size = aSize + pulse;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (25.0 / -mvPosition.z);
    gl_PointSize = clamp(gl_PointSize, 0.5, 8.0);
    gl_Position = projectionMatrix * mvPosition;
  }
`

const holoFragmentShader = /* glsl */ `
  varying vec3 vColor;
  varying float vDepth;
  varying float vPhase;

  uniform float uTime;
  uniform float uOpacity;

  void main() {
    // Sharp circular point with soft edge
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    // Core bright, edge fades — creates defined dot look
    float alpha = 1.0 - smoothstep(0.15, 0.5, dist);

    // Subtle flicker per particle
    float flicker = 0.9 + 0.1 * sin(uTime * 1.5 + vPhase * 6.28);

    // Inner particles: dimmer for depth perception
    float depthFade = mix(1.0, 0.5, vDepth);

    gl_FragColor = vec4(vColor * flicker * depthFade, alpha * uOpacity);
  }
`

/* ─── Deterministic pseudo-random ─── */
function hash(i: number, seed: number): number {
  const t = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453
  return t - Math.floor(t)
}

/* ─── Constants ─── */
const SURFACE_PARTICLES = 18000
const INNER_PARTICLES = 2000
const TOTAL = SURFACE_PARTICLES + INNER_PARTICLES

/* ─── Brain particle cloud from real mesh ─── */
function BrainCloud({ state }: { state: BrainState }) {
  const pointsRef = useRef<THREE.Points>(null)
  const gltf = useLoader(GLTFLoader, '/models/brain.glb')

  const { geometry, material } = useMemo(() => {
    let brainMesh: THREE.Mesh | null = null
    gltf.scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh && !brainMesh) {
        brainMesh = child as THREE.Mesh
      }
    })

    if (!brainMesh) throw new Error('No mesh found in brain model')

    const mesh = brainMesh as THREE.Mesh
    const geo = mesh.geometry.clone()

    geo.computeBoundingBox()
    const box = geo.boundingBox!
    const center = new THREE.Vector3()
    box.getCenter(center)
    const size = new THREE.Vector3()
    box.getSize(size)
    const maxDim = Math.max(size.x, size.y, size.z)
    const scale = 1.6 / maxDim

    geo.translate(-center.x, -center.y, -center.z)
    geo.scale(scale, scale, scale)
    geo.computeVertexNormals()

    const samplerMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial())
    const sampler = new MeshSurfaceSampler(samplerMesh).build()

    const positions = new Float32Array(TOTAL * 3)
    const colors = new Float32Array(TOTAL * 3)
    const sizes = new Float32Array(TOTAL)
    const phases = new Float32Array(TOTAL)
    const depths = new Float32Array(TOTAL)

    const tempPos = new THREE.Vector3()
    const tempNormal = new THREE.Vector3()

    // Surface particles
    for (let i = 0; i < SURFACE_PARTICLES; i++) {
      sampler.sample(tempPos, tempNormal)
      // Slight jitter along normal for organic feel
      const jitter = (hash(i, 3) - 0.5) * 0.015
      positions[i * 3] = tempPos.x + tempNormal.x * jitter
      positions[i * 3 + 1] = tempPos.y + tempNormal.y * jitter
      positions[i * 3 + 2] = tempPos.z + tempNormal.z * jitter
      depths[i] = 0
    }

    // Inner volume particles
    for (let i = 0; i < INNER_PARTICLES; i++) {
      const idx = SURFACE_PARTICLES + i
      sampler.sample(tempPos)
      const shrink = 0.25 + hash(i, 12) * 0.5
      positions[idx * 3] = tempPos.x * shrink
      positions[idx * 3 + 1] = tempPos.y * shrink
      positions[idx * 3 + 2] = tempPos.z * shrink
      depths[idx] = 1.0 - shrink
    }

    // Compute Y range for color gradient
    let minY = Infinity, maxY = -Infinity
    for (let i = 0; i < TOTAL; i++) {
      const y = positions[i * 3 + 1]
      if (y < minY) minY = y
      if (y > maxY) maxY = y
    }
    const rangeY = maxY - minY || 1

    for (let i = 0; i < TOTAL; i++) {
      const d = depths[i]
      const y = positions[i * 3 + 1]
      const hf = (y - minY) / rangeY // 0=bottom, 1=top

      if (d > 0.3) {
        // Inner: dimmer teal
        colors[i * 3] = 0.0
        colors[i * 3 + 1] = 0.25 + hf * 0.15
        colors[i * 3 + 2] = 0.35 + hf * 0.15
      } else {
        // Surface: bright cyan, slight variation by height
        colors[i * 3] = 0.0
        colors[i * 3 + 1] = 0.55 + hf * 0.35  // green channel: 0.55-0.9
        colors[i * 3 + 2] = 0.65 + hf * 0.35  // blue channel: 0.65-1.0
      }

      // Tiny points — key to seeing individual particles
      sizes[i] = d > 0.3
        ? 0.6 + hash(i, 30) * 0.8   // inner: 0.6-1.4
        : 0.3 + hash(i, 30) * 0.5   // surface: 0.3-0.8

      phases[i] = hash(i, 40) * Math.PI * 2
    }

    const bufGeo = new THREE.BufferGeometry()
    bufGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    bufGeo.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    bufGeo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
    bufGeo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))
    bufGeo.setAttribute('aDepth', new THREE.BufferAttribute(depths, 1))

    const mat = new THREE.ShaderMaterial({
      vertexShader: holoVertexShader,
      fragmentShader: holoFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uPulseSpeed: { value: 1.2 },
        uPulseAmp: { value: 0.15 },
        uOpacity: { value: 0.55 },
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })

    return { geometry: bufGeo, material: mat }
  }, [gltf])

  useFrame(({ clock }) => {
    if (!pointsRef.current) return
    const t = clock.getElapsedTime()
    const mat = pointsRef.current.material as THREE.ShaderMaterial

    const isThinking = state === 'thinking'
    const isResponding = state === 'responding'
    const isIdle = state === 'idle'

    mat.uniforms.uTime.value = t
    mat.uniforms.uPulseSpeed.value = isThinking ? 4.0 : isResponding ? 2.5 : 1.0
    mat.uniforms.uPulseAmp.value = isThinking ? 0.3 : isResponding ? 0.2 : 0.1
    mat.uniforms.uOpacity.value = isIdle ? 0.5 : 0.65

    // Slow auto-rotation
    const autoSpeed = isThinking ? 0.06 : isResponding ? 0.04 : 0.01
    pointsRef.current.rotation.y += autoSpeed * 0.016
  })

  return <points ref={pointsRef} geometry={geometry} material={material} />
}

/* ─── Scan ring ─── */
function ScanRing({ state }: { state: BrainState }) {
  const ringRef = useRef<THREE.LineLoop>(null)

  const ringPositions = useMemo(() => {
    const segments = 128
    const arr = new Float32Array(segments * 3)
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      arr[i * 3] = Math.cos(angle) * 1.0
      arr[i * 3 + 1] = 0
      arr[i * 3 + 2] = Math.sin(angle) * 0.95
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const t = clock.getElapsedTime()
    const speed = state === 'thinking' ? 1.5 : 0.4
    ringRef.current.position.y = Math.sin(t * speed) * 0.7
    const mat = ringRef.current.material as THREE.LineBasicMaterial
    mat.opacity = state === 'idle' ? 0.04 : state === 'thinking' ? 0.12 : 0.08
  })

  return (
    <lineLoop ref={ringRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[ringPositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color="#00F0FF"
        transparent
        opacity={0.04}
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
    const count = 60
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (hash(i, 50) - 0.5) * 6
      arr[i * 3 + 1] = (hash(i, 51) - 0.5) * 6
      arr[i * 3 + 2] = (hash(i, 52) - 0.5) * 6
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.004
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
        opacity={0.06}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

/* ─── Invisible click target ─── */
function ClickTarget({ onClick }: { onClick?: () => void }) {
  const pointerDown = useRef<{ x: number; y: number; time: number } | null>(null)

  return (
    <mesh
      visible={false}
      onPointerDown={(e) => {
        pointerDown.current = { x: e.clientX, y: e.clientY, time: Date.now() }
      }}
      onPointerUp={(e) => {
        if (!pointerDown.current || !onClick) return
        const dx = e.clientX - pointerDown.current.x
        const dy = e.clientY - pointerDown.current.y
        const dt = Date.now() - pointerDown.current.time
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8 && dt < 400) onClick()
        pointerDown.current = null
      }}
    >
      <sphereGeometry args={[1.5, 16, 16]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  )
}

/* ─── Loading placeholder ─── */
function BrainLoading() {
  const ref = useRef<THREE.Points>(null)
  const positions = useMemo(() => {
    const arr = new Float32Array(150 * 3)
    for (let i = 0; i < 150; i++) {
      const theta = hash(i, 1) * Math.PI * 2
      const phi = Math.acos(2 * hash(i, 2) - 1)
      const r = 0.5 + hash(i, 3) * 0.3
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.2
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.02}
        color="#00F0FF"
        transparent
        opacity={0.3}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}

/* ─── Scene ─── */
function BrainScene({ state, onClick }: { state: BrainState; onClick?: () => void }) {
  return (
    <>
      <Suspense fallback={<BrainLoading />}>
        <BrainCloud state={state} />
      </Suspense>
      <ScanRing state={state} />
      <AmbientParticles />
      <ClickTarget onClick={onClick} />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        rotateSpeed={0.5}
        dampingFactor={0.12}
        enableDamping
        minPolarAngle={Math.PI * 0.15}
        maxPolarAngle={Math.PI * 0.85}
      />
    </>
  )
}

/* ─── Public component ─── */
export function HoloBrain({ state = 'idle', size = 'md', className, onClick }: HoloBrainProps) {
  const sizeMap = {
    sm: 'h-32 w-32',
    md: 'h-48 w-48',
    lg: 'h-64 w-64',
    xl: 'h-[18rem] w-[18rem] md:h-[22rem] md:w-[22rem]',
  }

  return (
    <div className={`${sizeMap[size]} ${className || ''} cursor-pointer overflow-hidden`}>
      <Canvas
        camera={{ position: [0, 0.15, 3.5], fov: 34 }}
        dpr={[1, 1.5]}
        gl={{ alpha: true, antialias: false, powerPreference: 'high-performance' }}
        style={{ background: 'transparent' }}
      >
        <BrainScene state={state} onClick={onClick} />
      </Canvas>
    </div>
  )
}
