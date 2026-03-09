// Cache-busting comment to ensure fresh module loading
import { viewer } from './interface_model.js';
import { loadGeoJSON, initializeHeatmapControls, customDataSource } from './terrain_model.js?v=1';
import { initialize as initializeVehicles } from './vehicle_model.js';
import { initializeDistanceMeasurement, getMeasurementState, addMeasurementPointExternal } from './distance_measurement.js';
import { sessionManager } from './session_manager.js';

// Track loading states
let geoJsonLoaded = false;
let vehiclesLoaded = false;
let renderingComplete = false;

// Function to send rendering progress
function sendRenderingProgress(progress, message) {
    if (window.parent && window.parent !== window) {
        window.parent.postMessage({
            type: 'rendering_progress',
            progress: progress,
            message: message,
            timestamp: new Date().toISOString()
        }, '*');
    }
}

// Function to enable camera controls after rendering is complete
function enableCameraControls() {
    if (viewer && viewer.scene && viewer.scene.screenSpaceCameraController) {
        viewer.scene.screenSpaceCameraController.enableRotate = true;
        viewer.scene.screenSpaceCameraController.enableTranslate = true;
        viewer.scene.screenSpaceCameraController.enableZoom = true;
        viewer.scene.screenSpaceCameraController.enableTilt = true;
        viewer.scene.screenSpaceCameraController.enableLook = true;
        // Camera controls enabled
    }
}

// Function to check if all rendering is complete
function checkRenderingComplete() {
    if (geoJsonLoaded && vehiclesLoaded && !renderingComplete) {
        renderingComplete = true;

        // Place factory model on the surface (after all other data is loaded)
        const factoryPosition = Cesium.Cartesian3.fromDegrees(117.4490905100999, 4.70291486589133, -3);
        const factoryHeading = Cesium.Math.toRadians(95);
        const factoryOrientation = Cesium.Transforms.headingPitchRollQuaternion(
            factoryPosition,
            new Cesium.HeadingPitchRoll(factoryHeading, 0, 0)
        );
        viewer.entities.add({
            name: 'Factory',
            position: factoryPosition,
            orientation: factoryOrientation,
            model: {
                uri: '/static/model/FACTORY.glb',
                scale: 1.0,
                heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND
            }
        });

        // Enable camera controls
        enableCameraControls();
        
        // Send message to parent window
        if (window.parent && window.parent !== window) {
            window.parent.postMessage({
                type: 'rendering_complete',
                timestamp: new Date().toISOString()
            }, '*');
        }
    }
}

document.addEventListener('viewerInitialized', () => {
    // Viewer initialized

    // Disable camera controls initially to prevent lag during loading
    if (viewer && viewer.scene && viewer.scene.screenSpaceCameraController) {
        viewer.scene.screenSpaceCameraController.enableRotate = false;
        viewer.scene.screenSpaceCameraController.enableTranslate = false;
        viewer.scene.screenSpaceCameraController.enableZoom = false;
        viewer.scene.screenSpaceCameraController.enableTilt = false;
        viewer.scene.screenSpaceCameraController.enableLook = false;
        // Camera controls disabled during loading
    }

    // Initialize session manager first
    sessionManager.initialize();
    // Session manager initialized

    // Initialize UI controls
    initializeHeatmapControls();
    initializeDistanceMeasurement(viewer);

    // Initialize the vehicle visualization
    // Starting Vehicle Visualization
    sendRenderingProgress(10, 'Initializing vehicle visualization...');
    
    initializeVehicles(viewer).then(vehicleManager => {
        if (!vehicleManager) {
            vehiclesLoaded = true;
            checkRenderingComplete();
            return;
        }

        const vehicleDataSource = vehicleManager.entityManager.vehicleDataSource;
        vehiclesLoaded = true;
        sendRenderingProgress(60, 'Vehicle data loaded');

        // Fly camera to the first valid position from uploaded data
        const initPos = vehicleManager.getInitialPosition();
        if (initPos) {
            viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(initPos.longitude, initPos.latitude, 500),
                orientation: {
                    heading: Cesium.Math.toRadians(60),
                    pitch: Cesium.Math.toRadians(-70),
                    roll: Cesium.Math.toRadians(0)
                }
            });
        }

        checkRenderingComplete();

        if (viewer && viewer.screenSpaceEventHandler) {
            viewer.screenSpaceEventHandler.setInputAction(function onLeftClick(movement) {
                const measurementState = getMeasurementState();
                if (measurementState.isMeasuring) {
                    const ray = viewer.camera.getPickRay(movement.position);
                    const pickedPosition = viewer.scene.globe.pick(ray, viewer.scene);
                    if (Cesium.defined(pickedPosition)) {
                        addMeasurementPointExternal(pickedPosition);
                    }
                    return; 
                }
                
                const pickedObject = viewer.scene.pick(movement.position);
                if (Cesium.defined(pickedObject) && pickedObject.id) {
                    if (
                        (customDataSource && customDataSource.entities.contains(pickedObject.id)) ||
                        (vehicleDataSource && vehicleDataSource.entities.contains(pickedObject.id)) ||
                        viewer.entities.contains(pickedObject.id)
                    ) {
                        viewer.selectedEntity = pickedObject.id;
                    }
                }
            }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
        }
    }).catch(error => {
        console.error('Error loading vehicle visualization:', error);
        sendRenderingProgress(100, 'Error loading vehicle data');
    });

    // Load the GeoJSON data
    sendRenderingProgress(20, 'Loading map data...');
    loadGeoJSON().then(() => {
        geoJsonLoaded = true;
        // GeoJSON data loaded
        sendRenderingProgress(50, 'Map data loaded');
        checkRenderingComplete();
    }).catch(error => {
        console.error('Error loading GeoJSON data:', error);
        sendRenderingProgress(100, 'Error loading map data');
    });
    
    // Additional check for viewer readiness
    setTimeout(() => {
        if (viewer && viewer.scene && viewer.scene.globe) {
            sendRenderingProgress(90, 'Finalizing rendering...');
            // Wait a bit more for any final rendering
            setTimeout(() => {
                checkRenderingComplete();
            }, 1000);
        }
    }, 2000);
});
