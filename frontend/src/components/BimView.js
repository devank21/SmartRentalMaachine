import React, { Suspense } from "react";
// This line has been corrected
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Text, Environment } from "@react-three/drei";

// A simple placeholder for your actual 3D model
const ModelPlaceholder = () => {
  return (
    <mesh castShadow position={[0, 1, 0]}>
      <boxGeometry args={[2, 2, 2]} />
      <meshStandardMaterial color="royalblue" metalness={0.6} roughness={0.2} />
    </mesh>
  );
};

// A simple ground plane to receive shadows
const GroundPlane = () => {
  return (
    <mesh
      receiveShadow
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, -0.01, 0]}
    >
      <planeGeometry args={[20, 20]} />
      <meshStandardMaterial color="#888888" />
    </mesh>
  );
};

const BimView = ({ navigateTo }) => {
  return (
    <div className="view-container bim-container">
      <div className="button-container">
        <button className="nav-button" onClick={() => navigateTo("dashboard")}>
          Back to Dashboard
        </button>
      </div>

      <Canvas shadows camera={{ position: [10, 10, 10], fov: 35 }}>
        <ambientLight intensity={1.5} />

        <directionalLight
          castShadow
          position={[10, 15, 5]}
          intensity={1.5}
          shadow-mapSize-width={2048}
          shadow-mapSize-height={2048}
        />

        <axesHelper args={[5]} />

        <Suspense fallback={null}>
          <ModelPlaceholder />
          <GroundPlane />

          <Text
            position={[0, 3, 0]}
            fontSize={0.5}
            color="black"
            anchorX="center"
            anchorY="middle"
          >
            BIM Digital Twin
          </Text>

          <Environment preset="sunset" />
        </Suspense>

        <OrbitControls />
      </Canvas>
    </div>
  );
};

export default BimView;
