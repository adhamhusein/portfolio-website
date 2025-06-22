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
        console.log('Camera controls enabled');
    }
}

// Function to check if all rendering is complete
function checkRenderingComplete() {
    if (geoJsonLoaded && vehiclesLoaded && !renderingComplete) {
        renderingComplete = true;
        console.log('All rendering complete, notifying parent window');
        
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
    console.log('Viewer initialized, starting other initializations...');

    // Disable camera controls initially to prevent lag during loading
    if (viewer && viewer.scene && viewer.scene.screenSpaceCameraController) {
        viewer.scene.screenSpaceCameraController.enableRotate = false;
        viewer.scene.screenSpaceCameraController.enableTranslate = false;
        viewer.scene.screenSpaceCameraController.enableZoom = false;
        viewer.scene.screenSpaceCameraController.enableTilt = false;
        viewer.scene.screenSpaceCameraController.enableLook = false;
        console.log('Camera controls disabled during loading');
    }

    // Initialize session manager first
    sessionManager.initialize();
    console.log('Session manager initialized');

    // Initialize UI controls
    initializeHeatmapControls();
    initializeDistanceMeasurement(viewer);

    // Initialize the vehicle visualization
    console.log('🚛 Starting Vehicle Visualization...');
    sendRenderingProgress(10, 'Initializing vehicle visualization...');
    
    initializeVehicles(viewer).then(vehicleManager => {
        const vehicleDataSource = vehicleManager.entityManager.vehicleDataSource;
        vehiclesLoaded = true;
        console.log('Vehicle visualization loaded');
        sendRenderingProgress(60, 'Vehicle data loaded');
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
        console.log('GeoJSON data loaded');
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
