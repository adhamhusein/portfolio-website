import { viewer as viewerRef } from './interface_model.js';

// Distance measurement state
let isMeasuring = false;
let measurementPoints = [];
let measurementEntity = null;
let measurementLabel = null;
let segmentLabelEntities = [];
let totalDistance = 0;

// Create a data source for measurement entities
let measurementDataSource = null;
let localViewer = null;

// Initialize the data source when viewer is available
const initializeDataSource = () => {
    if (!localViewer) {
        console.error('Viewer not available for distance measurement');
        return false;
    }
    
    if (!measurementDataSource) {
        try {
            measurementDataSource = new Cesium.CustomDataSource('DistanceMeasurement');
            localViewer.dataSources.add(measurementDataSource);
            console.log('Distance measurement data source initialized');
            return true;
        } catch (error) {
            console.error('Failed to initialize measurement data source:', error);
            return false;
        }
    }
    return true;
};

// Distance measurement styles
const MEASUREMENT_STYLES = {
    point: {
        pixelSize: 8,
        color: Cesium.Color.YELLOW,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    line: {
        width: 3,
        material: Cesium.Color.YELLOW,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    },
    label: {
        font: 'bold 12pt sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: Cesium.Color.BLACK.withAlpha(0.7),
        backgroundPadding: new Cesium.Cartesian2(7, 5),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        pixelOffset: new Cesium.Cartesian2(0, -20)
    }
};

// Calculate distance between two points
const calculateDistance = (point1, point2) => {
    // Robustness checks for input points
    if (!point1 || !point2 || !(point1 instanceof Cesium.Cartesian3) || !(point2 instanceof Cesium.Cartesian3)) {
        console.error("Invalid input for calculateDistance. Points must be Cesium.Cartesian3 objects.", { point1, point2 });
        return 0;
    }

    try {
        // Use the direct straight-line distance calculation, which is more robust for points picked from the globe surface.
        const distance = Cesium.Cartesian3.distance(point1, point2);

        // Check for NaN result
        if (isNaN(distance)) {
            console.error("Distance calculation resulted in NaN.", { point1, point2 });
            return 0;
        }
        
        return distance;
    } catch (error) {
        console.error("Error in calculateDistance:", error, { point1, point2 });
        return 0; // Return 0 on error
    }
};

// Format distance for display
const formatDistance = (distance) => {
    // Handle invalid or zero distance
    if (isNaN(distance) || distance === 0) {
        return '0.0 m';
    }
    
    if (distance < 1000) {
        return `${distance.toFixed(1)} m`;
    } else {
        return `${(distance / 1000).toFixed(2)} km`;
    }
};

// Add a measurement point
const addMeasurementPoint = (position) => {
    if (!measurementDataSource) {
        console.error('Measurement data source not initialized');
        return null;
    }
    
    // Clone the position to ensure we have a unique instance and are not using a Cesium scratch variable.
    const clonedPosition = Cesium.Cartesian3.clone(position);

    try {
        console.log('Adding measurement point at:', clonedPosition);
        const point = measurementDataSource.entities.add({
            position: clonedPosition,
            point: MEASUREMENT_STYLES.point
        });
        
        measurementPoints.push({ position: clonedPosition, entity: point });
        console.log('Measurement point added. Total points:', measurementPoints.length);
        
        // Update the polyline if we have more than one point
        if (measurementPoints.length > 1) {
            updateMeasurementLine();
        }
        
        return point;
    } catch (error) {
        console.error('Error adding measurement point:', error);
        return null;
    }
};

// Update the measurement line
const updateMeasurementLine = () => {
    if (measurementEntity) {
        measurementDataSource.entities.remove(measurementEntity);
        measurementEntity = null;
    }
    
    if (measurementLabel) {
        measurementDataSource.entities.remove(measurementLabel);
        measurementLabel = null;
    }

    // Remove old segment labels before adding new ones
    segmentLabelEntities.forEach(entity => measurementDataSource.entities.remove(entity));
    segmentLabelEntities = [];
    
    if (measurementPoints.length < 2) return;
    
    const positions = measurementPoints.map(p => p.position);
    
    // Create polyline
    measurementEntity = measurementDataSource.entities.add({
        polyline: {
            positions: positions,
            width: MEASUREMENT_STYLES.line.width,
            material: MEASUREMENT_STYLES.line.material,
            heightReference: MEASUREMENT_STYLES.line.heightReference
        }
    });
    
    // Calculate total distance and segment distances
    totalDistance = 0;
    const segmentDistances = [];
    
    for (let i = 1; i < measurementPoints.length; i++) {
        const segmentDistance = calculateDistance(
            measurementPoints[i-1].position,
            measurementPoints[i].position
        );
        segmentDistances.push(segmentDistance);
        totalDistance += segmentDistance;
    }
    
    // Add distance labels for each segment
    segmentDistances.forEach((segmentDistance, index) => {
        const midPoint = Cesium.Cartesian3.lerp(
            measurementPoints[index].position,
            measurementPoints[index + 1].position,
            0.5,
            new Cesium.Cartesian3()
        );
        
        const labelEntity = measurementDataSource.entities.add({
            position: midPoint,
            label: {
                text: formatDistance(segmentDistance),
                font: 'bold 10pt sans-serif',
                fillColor: Cesium.Color.YELLOW,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 1,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                showBackground: true,
                backgroundColor: Cesium.Color.BLACK.withAlpha(0.7),
                backgroundPadding: new Cesium.Cartesian2(5, 3),
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                pixelOffset: new Cesium.Cartesian2(0, -15)
            }
        });
        segmentLabelEntities.push(labelEntity);
    });
    
    // Add total distance label at the last point
    const lastPoint = measurementPoints[measurementPoints.length - 1];
    measurementLabel = measurementDataSource.entities.add({
        position: lastPoint.position,
        label: {
            text: `Total: ${formatDistance(totalDistance)}`,
            ...MEASUREMENT_STYLES.label
        }
    });
};

// Clear all measurement data
const clearMeasurement = () => {
    if (measurementDataSource) {
        // Remove all entities from the measurement data source
        measurementDataSource.entities.removeAll();
    }
    
    measurementPoints = [];
    measurementEntity = null;
    measurementLabel = null;
    segmentLabelEntities = []; // Also clear segment labels
    totalDistance = 0;
    
    // Reset cursor if not measuring
    if (!isMeasuring) {
        document.body.style.cursor = 'default';
    }
    
    console.log('Measurement cleared');
};

// Toggle measurement state
const toggleMeasurement = () => {
    if (isMeasuring) {
        finishMeasurement();
    } else {
        startMeasurement();
    }
    console.log('Measurement mode toggled');
}

// Handle click events for measurement
const handleMeasurementClick = (movement) => {
    console.log('Measurement click handler called, isMeasuring:', isMeasuring);
    if (!isMeasuring) return;
    
    try {
        const pickedPosition = localViewer.camera.pickEllipsoid(movement.position, localViewer.scene.globe.ellipsoid);
        console.log('Picked position:', pickedPosition);
        if (pickedPosition) {
            addMeasurementPoint(pickedPosition);
            // Prevent the click from being processed by other handlers
            movement.stopPropagation();
        } else {
            console.log('No position picked from click');
        }
    } catch (error) {
        console.error('Error in measurement click handler:', error);
    }
};

// Handle double-click to finish measurement
const handleMeasurementDoubleClick = (movement) => {
    if (!isMeasuring) return;
    
    // Prevent double-click from being processed by other handlers
    movement.stopPropagation();
    
    // Finish the measurement
    finishMeasurement();
};

// Finish the current measurement
const finishMeasurement = () => {
    if (measurementPoints.length > 0) {
        console.log(`Measurement completed: ${formatDistance(totalDistance)}`);
        
        // Keep the measurement visible but stop measuring
        isMeasuring = false;
        updateMeasurementButton();
    }
};

// Start a new measurement
const startMeasurement = () => {
    console.log('Starting measurement...');
    
    // Ensure data source is initialized
    if (!initializeDataSource()) {
        console.error('Cannot start measurement: data source not available');
        return;
    }
    
    clearMeasurement();
    isMeasuring = true;
    updateMeasurementButton();
    console.log('Distance measurement started. Click to add points, double-click to finish.');
};

// Update the measurement button state
const updateMeasurementButton = () => {
    const button = document.getElementById('distance-measurement-btn');
    if (button) {
        if (isMeasuring) {
            const pointText = measurementPoints.length > 0 ? ` (${measurementPoints.length} points)` : '';
            button.textContent = `Stop Measuring${pointText}`;
            button.style.background = '#dc3545';
            // Change cursor to indicate measurement mode
            document.body.style.cursor = 'crosshair';
        } else {
            button.textContent = 'Start Measuring';
            button.style.background = '#28a745';
            // Reset cursor
            document.body.style.cursor = 'default';
        }
    }
};

// Handle keyboard events for measurement
const handleMeasurementKeyDown = (event) => {
    if (!isMeasuring) return;
    
    switch (event.key) {
        case 'Enter':
            finishMeasurement();
            event.preventDefault();
            break;
        case 'Escape':
            clearMeasurement();
            isMeasuring = false;
            updateMeasurementButton();
            event.preventDefault();
            break;
    }
};

// Initialize distance measurement controls
export const initializeDistanceMeasurement = (viewer) => {
    localViewer = viewer;
    if (!localViewer) {
        console.error('Viewer not available for distance measurement initialization');
        return;
    }

    if (!initializeDataSource()) {
        console.error('Failed to initialize distance measurement data source');
        return;
    }
    
    const startBtn = document.getElementById('distance-measurement-btn');
    const clearBtn = document.getElementById('clear-measurement-btn');

    if (!startBtn || !clearBtn) {
        console.error('Measurement buttons not found in the DOM');
        return;
    }

    startBtn.addEventListener('click', toggleMeasurement);
    clearBtn.addEventListener('click', clearMeasurement);

    // Use a shared screen space event handler if possible
    const handler = new Cesium.ScreenSpaceEventHandler(localViewer.scene.canvas);

    handler.setInputAction((movement) => {
        if (isMeasuring) {
            handleMeasurementClick(movement);
        }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    handler.setInputAction((movement) => {
        if (isMeasuring) {
            handleMeasurementDoubleClick(movement);
        }
    }, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

    document.addEventListener('keydown', handleMeasurementKeyDown);

    console.log('Distance measurement functionality initialized');
};

// Export functions for external use
export const getMeasurementState = () => ({
    isMeasuring,
    totalDistance,
    pointCount: measurementPoints.length
});

export const clearAllMeasurements = clearMeasurement;

// Export the addMeasurementPoint function for external use
export const addMeasurementPointExternal = addMeasurementPoint; 