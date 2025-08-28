import React, { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  Text,
  Box,
  Cylinder,
  Environment,
} from "@react-three/drei";

// This component represents a piece of equipment in the 3D scene.
// In a real scenario, you would replace the <Box> or <Cylinder>
// with a loaded 3D model (e.g., from a GLTF file).
const Equipment = ({ position, name, status }) => {
  const color =
    status === "In-Use"
      ? "#f39c12"
      : status === "Maintenance"
      ? "#c0392b"
      : "#27ae60";

  return (
    <group position={position}>
      <Box args={[2, 2, 4]} position={[0, 1, 0]}>
        <meshStandardMaterial color={color} />
      </Box>
      <Text
        position={[0, 3.5, 0]}
        color="white"
        fontSize={0.5}
        anchorX="center"
        anchorY="middle"
      >
        {name}
      </Text>
    </group>
  );
};

const BimView = ({ navigateTo }) => {
  // In a real application, this data would come from your API
  const equipmentData = [
    { name: "CAT-D6T", status: "In-Use", position: [-10, 0, 5] },
    { name: "CAT-320", status: "In-Use", position: [10, 0, -5] },
    { name: "CAT-950M", status: "Available", position: [0, 0, 10] },
    { name: "CAT-336", status: "Maintenance", position: [15, 0, 15] },
  ];

  return (
    <div className="view-container bim-container">
      <div className="bim-header">
        <h2>BIM Site Viewer</h2>
        <p>
          This is a 3D representation of the job site. Click and drag to
          navigate.
        </p>
      </div>
      <Canvas camera={{ position: [25, 25, 25], fov: 25 }}>
        <Suspense fallback={null}>
          {/* Lighting and Environment */}
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} />
          <Environment preset="sunset" />

          {/* Controls to navigate the scene */}
          <OrbitControls />

          {/* The ground plane */}
          <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
            <planeGeometry args={[100, 100]} />
            <meshStandardMaterial color="#555" />
          </mesh>

          {/* Placeholder for a building structure */}
          <Box args={[30, 10, 20]} position={[0, 5, 0]}>
            <meshStandardMaterial color="gray" transparent opacity={0.3} />
          </Box>

          {/* Render the equipment from our data */}
          {equipmentData.map((eq) => (
            <Equipment key={eq.name} {...eq} />
          ))}
        </Suspense>
      </Canvas>
    </div>
  );
};

export default BimView;
