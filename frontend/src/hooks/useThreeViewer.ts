import { useCallback, useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

interface SceneState {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  controls: OrbitControls;
  model: THREE.Object3D | null;
  clipPlane: THREE.Plane;
  revealAt: number;
  revealFrom: number;
  revealTo: number;
  reduceMotion: boolean;
  loader: GLTFLoader;
}

const REVEAL_MS = 900;

function setClipping(object: THREE.Object3D, planes: THREE.Plane[]): void {
  object.traverse((node) => {
    const material = (node as THREE.Mesh).material;
    if (!material) return;
    const apply = (m: THREE.Material) => {
      m.clippingPlanes = planes;
      m.needsUpdate = true;
    };
    if (Array.isArray(material)) material.forEach(apply);
    else apply(material);
  });
}

function disposeMaterial(material: THREE.Material): void {
  for (const value of Object.values(material as unknown as Record<string, unknown>)) {
    if (value && (value as THREE.Texture).isTexture) (value as THREE.Texture).dispose();
  }
  material.dispose();
}

function disposeObject(object: THREE.Object3D): void {
  object.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (mesh.geometry) mesh.geometry.dispose();
    const material = mesh.material;
    if (Array.isArray(material)) material.forEach(disposeMaterial);
    else if (material) disposeMaterial(material);
  });
}

function frame(object: THREE.Object3D, s: SceneState): void {
  const box = new THREE.Box3().setFromObject(object);
  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  box.getCenter(center);
  box.getSize(size);
  const maxSize = Math.max(size.x, size.y, size.z, 1);
  const fit = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(s.camera.fov) / 2));
  const dir = new THREE.Vector3(1, 0.8, 1).normalize();
  s.camera.position.copy(center).add(dir.multiplyScalar(fit * 1.6));
  s.camera.near = Math.max(fit / 100, 0.001);
  s.camera.far = Math.max(fit * 100, maxSize * 10);
  s.camera.lookAt(center);
  s.camera.updateProjectionMatrix();
  s.controls.target.copy(center);
  s.controls.update();
}

export interface UseThreeViewerResult {
  containerRef: React.RefObject<HTMLDivElement>;
  loadGlb: (url: string) => Promise<void>;
  clear: () => void;
}

export function useThreeViewer(): UseThreeViewerResult {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<SceneState | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight || 1,
      0.1,
      100,
    );
    camera.position.set(2.5, 2, 2.5);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.92;
    renderer.localClippingEnabled = true;
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const pmrem = new THREE.PMREMGenerator(renderer);
    const roomEnv = new RoomEnvironment();
    const envTexture = pmrem.fromScene(roomEnv, 0.04).texture;
    roomEnv.dispose();
    scene.environment = envTexture;
    scene.environmentIntensity = 0.42;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = !reduceMotion;
    controls.autoRotateSpeed = 0.55;
    const stopAutoRotate = () => {
      controls.autoRotate = false;
    };
    controls.addEventListener("start", stopAutoRotate);

    scene.add(new THREE.HemisphereLight(0xccd6ff, 0x0b0b12, 0.18));
    const key = new THREE.DirectionalLight(0xffffff, 0.95);
    key.position.set(3, 5, 2);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x8b7cf6, 0.7);
    rim.position.set(-4, 2.5, -4);
    scene.add(rim);

    const state: SceneState = {
      scene,
      camera,
      renderer,
      controls,
      model: null,
      clipPlane: new THREE.Plane(new THREE.Vector3(0, -1, 0), 0),
      revealAt: 0,
      revealFrom: 0,
      revealTo: 0,
      reduceMotion,
      loader: new GLTFLoader(),
    };
    sceneRef.current = state;

    renderer.setAnimationLoop(() => {
      if (state.model && state.revealAt) {
        const t = Math.min((performance.now() - state.revealAt) / REVEAL_MS, 1);
        const eased = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        state.clipPlane.constant = state.revealFrom + (state.revealTo - state.revealFrom) * eased;
        if (t >= 1) {
          setClipping(state.model, []);
          state.revealAt = 0;
        }
      }
      controls.update();
      renderer.render(scene, camera);
    });

    const ro = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w <= 0 || h <= 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      controls.removeEventListener("start", stopAutoRotate);
      controls.dispose();
      renderer.setAnimationLoop(null);
      if (state.model) disposeObject(state.model);
      envTexture.dispose();
      pmrem.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement);
      }
      sceneRef.current = null;
    };
  }, []);

  const loadGlb = useCallback((url: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const s = sceneRef.current;
      if (!s) return reject(new Error("viewer not mounted"));
      if (s.model) {
        s.scene.remove(s.model);
        disposeObject(s.model);
        s.model = null;
      }
      s.loader.load(
        url,
        (gltf) => {
          s.scene.add(gltf.scene);
          s.model = gltf.scene;
          frame(gltf.scene, s);
          s.controls.autoRotate = !s.reduceMotion;
          if (s.reduceMotion) {
            setClipping(gltf.scene, []);
            s.revealAt = 0;
          } else {
            const box = new THREE.Box3().setFromObject(gltf.scene);
            const margin = Math.max((box.max.y - box.min.y) * 0.02, 0.001);
            s.revealFrom = box.min.y - margin;
            s.revealTo = box.max.y + margin;
            s.clipPlane.constant = s.revealFrom;
            setClipping(gltf.scene, [s.clipPlane]);
            s.revealAt = performance.now();
          }
          resolve();
        },
        undefined,
        (err) => reject(err instanceof Error ? err : new Error("GLB failed to load")),
      );
    });
  }, []);

  const clear = useCallback(() => {
    const s = sceneRef.current;
    if (s && s.model) {
      s.scene.remove(s.model);
      disposeObject(s.model);
      s.model = null;
    }
  }, []);

  return { containerRef, loadGlb, clear };
}
