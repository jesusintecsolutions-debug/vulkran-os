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

    // Pulsing size
    float pulse = sin(uTime * uPulseSpeed + aPhase) * uPulseAmp;
    float size = aSize + pulse;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (300.0 / -mvPosition.z);
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
    // Soft circular point
    float dist = length(gl_PointCoord - vec2(0.5));
    if (dist > 0.5) discard;

    // Soft radial falloff — gaussian-ish
    float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
    alpha *= alpha; // sharper falloff for more defined points

    // Slight shimmer based on depth
    float shimmer = 0.85 + 0.15 * sin(uTime * 2.0 + vPhase * 6.28);

    // Inner particles glow more
    float glow = vDepth > 0.3 ? 1.4 : 1.0;

    gl_FragColor = vec4(vColor * shimmer * glow, alpha * uOpacity);
  }
`

/* ─── Deterministic pseudo-random ─── */
function hash(i: number, seed: number): number {
  const t = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453
  return t - Math.floor(t)
}

/* ─── Constants ─── */
const SURFACE_PARTICLES = 12000
const INNER_PARTICLES = 1500
const TOTAL = SURFACE_PARTICLES + INNER_PARTICLES

/* ─── Brain particle cloud from real mesh ─── */
function BrainCloud({ state }: { state: BrainState }) {
  const pointsRef = useRef<THREE.Points>(null)
  const gltf = useLoader(GLTFLoader, '/models/brain.glb')

  const { geometry, material } = useMemo(() => {
    // Find the brain mesh in the loaded model
    let brainMesh: THREE.Mesh | null = null
    gltf.scene.traverse((child) => {
      if ((child as THREE.Mesh).isMesh && !brainMesh) {
        brainMesh = child as THREE.Mesh
      }
    })

    if (!brainMesh) {
      throw new Error('No mesh found in brain model')
    }

    // Normalize the mesh: center it and scale to unit size
    const mesh = brainMesh as THREE.Mesh
    const geo = mesh.geometry.clone()

    // Compute bounding box for normalization
    geo.computeBoundingBox()
    const box = geo.boundingBox!
    const center = new THREE.Vector3()
    box.getCenter(center)
    const size = new THREE.Vector3()
    box.getSize(size)
    const maxDim = Math.max(size.x, size.y, size.z)
    const scale = 1.6 / maxDim // Normalize to ~1.6 units across (fits within container)

    // Apply centering + scaling to geometry
    geo.translate(-center.x, -center.y, -center.z)
    geo.scale(scale, scale, scale)

    // Ensure we have normals for sampling
    geo.computeVertexNormals()

    // Build sampler
    const samplerMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial())
    const sampler = new MeshSurfaceSampler(samplerMesh).build()

    // Sample particles
    const positions = new Float32Array(TOTAL * 3)
    const colors = new Float32Array(TOTAL * 3)
    const sizes = new Float32Array(TOTAL)
    const phases = new Float32Array(TOTAL)
    const depths = new Float32Array(TOTAL)

    const tempPos = new THREE.Vector3()
    const tempNormal = new THREE.Vector3()

    // Surface particles — dense shell
    for (let i = 0; i < SURFACE_PARTICLES; i++) {
      sampler.sample(tempPos, tempNormal)

      // Slight outward jitter along normal for volume
      const jitter = (hash(i, 3) - 0.5) * 0.02
      positions[i * 3] = tempPos.x + tempNormal.x * jitter
      positions[i * 3 + 1] = tempPos.y + tempNormal.y * jitter
      positions[i * 3 + 2] = tempPos.z + tempNormal.z * jitter
      depths[i] = 0
    }

    // Inner volume particles — sparser, for core glow
    for (let i = 0; i < INNER_PARTICLES; i++) {
      const idx = SURFACE_PARTICLES + i
      sampler.sample(tempPos)

      const shrink = 0.2 + hash(i, 12) * 0.55 // 20%-75% depth
      positions[idx * 3] = tempPos.x * shrink
      positions[idx * 3 + 1] = tempPos.y * shrink
      positions[idx * 3 + 2] = tempPos.z * shrink
      depths[idx] = 1.0 - shrink
    }

    // Compute color & size for each particle
    // Get bounding box of sampled positions
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
      const x = positions[i * 3]

      // Normalized height (0=bottom, 1=top)
      const hf = (y - minY) / rangeY

      // Cyan core (#00F0FF) → teal edge (#006080) with height variation
      if (d > 0.3) {
        // Inner particles: deep blue/teal, brighter
        colors[i * 3] = 0.0
        colors[i * 3 + 1] = 0.5 + hf * 0.4
        colors[i * 3 + 2] = 0.7 + hf * 0.3
      } else {
        // Surface particles: cyan with subtle variation
        const side = Math.abs(x) * 0.3
        colors[i * 3] = 0.0 + side * 0.05
        colors[i * 3 + 1] = 0.75 + hf * 0.2
        colors[i * 3 + 2] = 0.9 + hf * 0.1
      }

      // Size: surface = tiny dense points, inner = slightly larger glow dots
      sizes[i] = d > 0.3
        ? 2.5 + hash(i, 30) * 3.5  // inner
        : 1.0 + hash(i, 30) * 2.0  // surface

      phases[i] = hash(i, 40) * Math.PI * 2
    }

    // Build buffer geometry
    const bufGeo = new THREE.BufferGeometry()
    bufGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    bufGeo.setAttribute('aColor', new THREE.BufferAttribute(colors, 3))
    bufGeo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
    bufGeo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))
    bufGeo.setAttribute('aDepth', new THREE.BufferAttribute(depths, 1))

    // Shader material
    const mat = new THREE.ShaderMaterial({
      vertexShader: holoVertexShader,
      fragmentShader: holoFragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uPulseSpeed: { value: 1.2 },
        uPulseAmp: { value: 0.3 },
        uOpacity: { value: 0.85 },
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

    // State-driven parameters
    const isThinking = state === 'thinking'
    const isResponding = state === 'responding'
    const isIdle = state === 'idle'

    mat.uniforms.uTime.value = t
    mat.uniforms.uPulseSpeed.value = isThinking ? 5.0 : isResponding ? 3.0 : 1.2
    mat.uniforms.uPulseAmp.value = isThinking ? 1.0 : isResponding ? 0.6 : 0.3
    mat.uniforms.uOpacity.value = isIdle ? 0.8 : 0.95

    // Slow auto-rotation
    const autoSpeed = isThinking ? 0.08 : isResponding ? 0.05 : 0.012
    pointsRef.current.rotation.y += autoSpeed * 0.016
  })

  return <points ref={pointsRef} geometry={geometry} material={material} />
}

/* ─── Scan line — thin glowing ring ─── */
function ScanRing({ state }: { state: BrainState }) {
  const ringRef = useRef<THREE.LineLoop>(null)

  const ringPositions = useMemo(() => {
    const segments = 128
    const arr = new Float32Array(segments * 3)
    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * Math.PI * 2
      arr[i * 3] = Math.cos(angle) * 1.05
      arr[i * 3 + 1] = 0
      arr[i * 3 + 2] = Math.sin(angle) * 1.05
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (!ringRef.current) return
    const t = clock.getElapsedTime()
    const speed = state === 'thinking' ? 1.8 : 0.5
    ringRef.current.position.y = Math.sin(t * speed) * 0.8

    const mat = ringRef.current.material as THREE.LineBasicMaterial
    mat.opacity = state === 'idle' ? 0.03 : state === 'thinking' ? 0.15 : 0.08
  })

  return (
    <lineLoop ref={ringRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[ringPositions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color="#00F0FF"
        transparent
        opacity={0.05}
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
    const count = 80
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (hash(i, 50) - 0.5) * 6
      arr[i * 3 + 1] = (hash(i, 51) - 0.5) * 6
      arr[i * 3 + 2] = (hash(i, 52) - 0.5) * 6
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.005
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
        opacity={0.08}
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
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8 && dt < 400) {
          onClick()
        }
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
    const arr = new Float32Array(200 * 3)
    for (let i = 0; i < 200; i++) {
      const theta = hash(i, 1) * Math.PI * 2
      const phi = Math.acos(2 * hash(i, 2) - 1)
      const r = 0.6 + hash(i, 3) * 0.4
      arr[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  useFrame(({ clock }) => {
    if (ref.current) ref.current.rotation.y = clock.getElapsedTime() * 0.3
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.03}
        color="#00F0FF"
        transparent
        opacity={0.4}
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
