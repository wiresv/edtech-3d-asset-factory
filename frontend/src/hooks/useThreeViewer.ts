import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

interface SceneState {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  renderer: THREE.WebGLRenderer;
  controls: OrbitControls;
  model: THREE.Object3D | null;
  loader: GLTFLoader;
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

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1117);
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight || 1,
      0.1,
      100,
    );
    camera.position.set(2.5, 2, 2.5);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 3));
    const key = new THREE.DirectionalLight(0xffffff, 2);
    key.position.set(3, 4, 2);
    scene.add(key);

    const state: SceneState = {
      scene,
      camera,
      renderer,
      controls,
      model: null,
      loader: new GLTFLoader(),
    };
    sceneRef.current = state;

    renderer.setAnimationLoop(() => {
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
      renderer.setAnimationLoop(null);
      renderer.dispose();
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement);
      }
      sceneRef.current = null;
    };
  }, []);

  function loadGlb(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const s = sceneRef.current;
      if (!s) return reject(new Error("viewer not mounted"));
      if (s.model) {
        s.scene.remove(s.model);
        s.model = null;
      }
      s.loader.load(
        url,
        (gltf) => {
          s.scene.add(gltf.scene);
          s.model = gltf.scene;
          frame(gltf.scene, s);
          resolve();
        },
        undefined,
        (err) => reject(err instanceof Error ? err : new Error("GLB failed to load")),
      );
    });
  }

  function clear() {
    const s = sceneRef.current;
    if (s && s.model) {
      s.scene.remove(s.model);
      s.model = null;
    }
  }

  return { containerRef, loadGlb, clear };
}
