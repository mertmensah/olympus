import { useEffect, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export default function ModelViewer({ modelUrl, onStatusChange }) {
  const containerRef = useRef(null);
  const frameRef = useRef(null);

  useEffect(() => {
    if (!modelUrl || !containerRef.current) {
      return;
    }
    onStatusChange?.({ level: "info", message: `Loading model from ${modelUrl}` });

    // Initialize Three.js scene
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    // Camera setup
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.set(0, 1.5, 3);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    containerRef.current.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 10, 5);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 3;

    // Load model
    let modelRoot = null;
    const loader = new GLTFLoader();
    loader.load(
      modelUrl,
      (gltf) => {
        const model = gltf.scene;
        modelRoot = model;
        model.position.set(0, 0, 0);
        
        // Center and scale model
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        
        const maxDim = Math.max(size.x, size.y, size.z) || 1;
        const scale = 2 / maxDim;
        model.scale.multiplyScalar(scale);
        
        model.position.sub(center.multiplyScalar(scale));
        
        scene.add(model);
        onStatusChange?.({
          level: "success",
          message: `Model loaded: ${(size.x * size.y * size.z).toFixed(2)} scene volume`,
        });
      },
      (progress) => {
        if (progress.total > 0) {
          onStatusChange?.({
            level: "info",
            message: `Loading model: ${((progress.loaded / progress.total) * 100).toFixed(0)}%`,
          });
        }
      },
      (error) => {
        const msg = error?.message || String(error);
        onStatusChange?.({ level: "error", message: `Model load failed: ${msg}` });
        console.error("Error loading model:", error);
      }
    );

    // Animation loop
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle window resize
    const handleResize = () => {
      if (!containerRef.current) return;
      
      const newWidth = containerRef.current.clientWidth;
      const newHeight = containerRef.current.clientHeight;
      
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
      window.removeEventListener("resize", handleResize);
      controls.dispose();
      if (modelRoot) {
        scene.remove(modelRoot);
      }
      renderer.dispose();
      if (containerRef.current?.contains(renderer.domElement)) {
        containerRef.current.removeChild(renderer.domElement);
      }
    };
  }, [modelUrl, onStatusChange]);

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: "500px",
        borderRadius: "8px",
        overflow: "hidden",
        backgroundColor: "#1a1a2e",
      }}
    />
  );
}
