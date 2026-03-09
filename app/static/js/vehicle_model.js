// =============================
//  VEHICLE VISUALIZATION MODULE
// =============================

// No direct import of viewer, it will be passed in
// import {viewer} from './interface_model.js';
import { sessionManager } from './session_manager.js';

// Centralized configuration for all parameters and file paths
const CONFIG = {
    CSV: {
        DATA_PATH: '/static/dataset/datasheet12.csv', // Will be updated by session manager
        COLUMNS: {
            MOBILE_ID: 0,
            REPORT_TIME: 1,
            MOBILE_TYPE_ID: 2,
            MOBILE_ACTIVITY_ID: 3,
            MOBILE_STATUS_ID: 4,
            POS_LON: 5,
            POS_LAT: 6,
            POS_ALT: 7,
            POS_SPEED: 8,
            POS_DIR: 9,
            PLM_PAYLOAD: 10,
            PLM_INC: 11,
            PLM_STATUS: 12,
            IS_REVERSED: 13,
            VESSEL_ANGLE: 14,
            PLM_STATE: 15,
            REPORT_TIME_DISPLAY: 16
        }
    },
    HEADING_OFFSETS: {
        DEFAULT: -90,
        PLM_STATUS_5: 270
    },
    SPEED_THRESHOLD: 1.0,
    MODEL_PATHS: {
        HD785: '/static/model/HD785.glb',
        EXCAVATOR: '/static/model/PC2000.glb'
    },
    LABEL: {
        FONT: '20px sans-serif',
        DISTANCE_RANGE: [0.0, 1000.0],
        EYE_OFFSET: [0, 15, 0]
    },
    INTERPOLATION: {
        DEGREE: 1,
        ALGORITHM: Cesium.LinearApproximation
    },
    TIMELINE: {
        MULTIPLIER: 1
    }
};

// Make CONFIG available globally for session manager
window.VEHICLE_CONFIG = CONFIG;

// Vehicle telemetry data point
class VehicleDataPoint {
    constructor(mobileId, reportTime, longitude, latitude, speed, heading, plmStatus, mobileTypeId, isReversed, plmPayload, mobileActivityId, vesselAngle, plmInc, mobileStatusId, posAlt, plmState, reportTimeDisplay) {
        this.mobileId = mobileId;
        this.reportTime = reportTime;
        this.longitude = longitude;
        this.latitude = latitude;
        this.speed = speed;
        this.heading = heading;
        this.plmStatus = plmStatus;
        this.mobileTypeId = mobileTypeId;
        this.isReversed = isReversed;
        this.plmPayload = plmPayload;
        this.mobileActivityId = mobileActivityId;
        this.vesselAngle = vesselAngle;
        this.plmInc = plmInc;
        this.mobileStatusId = mobileStatusId;
        this.posAlt = posAlt;
        this.plmState = plmState;
        this.reportTimeDisplay = reportTimeDisplay;
    }

    getTime() {
        return Cesium.JulianDate.fromDate(new Date(this.reportTime));
    }

    getCartesian() {
        return Cesium.Cartesian3.fromDegrees(this.longitude, this.latitude, 0.0);
    }

    getHeadingOffset() {
        return this.plmStatus === 5 ? CONFIG.HEADING_OFFSETS.PLM_STATUS_5 : CONFIG.HEADING_OFFSETS.DEFAULT;
    }

    isStationary() {
        return this.speed < CONFIG.SPEED_THRESHOLD;
    }

    isMovingBackward() {
        return this.isReversed === 1;
    }
}

// CSV Data Loader and Parser
class CSVDataLoader {
    static async loadVehicleData() {
        try {
            // Initialize session manager and update data source
            sessionManager.initialize();

            // Skip loading if no real session data (default sample files don't exist)
            if (!sessionManager.hasDataFiles()) return {};

            CONFIG.CSV.DATA_PATH = sessionManager.getPositionDataUrl();
            
            const response = await fetch(CONFIG.CSV.DATA_PATH);
            if (!response.ok) return {};
            const csvText = await response.text();
            const rows = csvText.split('\n').slice(1);
            return this.parseRows(rows);
        } catch (error) {
            console.error('Error loading CSV:', error);
            return {};
        }
    }

    static parseRows(rows) {
        const unitData = {};
        rows.filter(row => row.trim()).forEach(row => {
            const columns = row.split(',');
            const dataPoint = this.createDataPoint(columns);
            if (!unitData[dataPoint.mobileId]) unitData[dataPoint.mobileId] = [];
            unitData[dataPoint.mobileId].push(dataPoint);
        });
        return unitData;
    }

    static createDataPoint(columns) {
        const C = CONFIG.CSV.COLUMNS;
        return new VehicleDataPoint(
            columns[C.MOBILE_ID],
            columns[C.REPORT_TIME],
            parseFloat(columns[C.POS_LON]),
            parseFloat(columns[C.POS_LAT]),
            parseFloat(columns[C.POS_SPEED]),
            parseFloat(columns[C.POS_DIR]),
            parseFloat(columns[C.PLM_STATUS]),
            parseInt(columns[C.MOBILE_TYPE_ID]),
            parseInt(columns[C.IS_REVERSED]),
            parseFloat(columns[C.PLM_PAYLOAD]),
            parseInt(columns[C.MOBILE_ACTIVITY_ID]),
            parseFloat(columns[C.VESSEL_ANGLE]),
            parseFloat(columns[C.PLM_INC]),
            columns[C.MOBILE_STATUS_ID],
            parseFloat(columns[C.POS_ALT]),
            columns[C.PLM_STATE],
            columns[C.REPORT_TIME_DISPLAY]
        );
    }
}

// Vehicle Entity Manager: Handles Cesium entity creation and configuration
export class VehicleEntityManager {
    constructor(viewer) {
        if (!viewer) {
            throw new Error("Viewer instance is required for VehicleEntityManager.");
        }
        this.viewer = viewer;
        // Use CustomDataSource for efficient management
        this.vehicleDataSource = new Cesium.CustomDataSource('Vehicles');
        this.trajectoryDataSource = new Cesium.CustomDataSource('Trajectories');
        this.viewer.dataSources.add(this.vehicleDataSource);
        this.viewer.dataSources.add(this.trajectoryDataSource);
        this.entities = new Map();
        this.trajectories = new Map();
    }

    createVehicle(unitId, dataPoints) {
        const mobileTypeId = dataPoints[0].mobileTypeId;
        const position = this._createPositionProperty(dataPoints);
        const orientation = this._createOrientationProperty(dataPoints);
        const velocityProperty = new Cesium.VelocityVectorProperty(position, false);
        // Trajectory polyline (hidden by default)
        const trajectory = this.trajectoryDataSource.entities.add({
            polyline: {
                positions: dataPoints.map(dp => dp.getCartesian()),
                width: 3,
                material: Cesium.Color.YELLOW.withAlpha(0.7),
                clampToGround: false
            },
            show: false
        });
        this.trajectories.set(unitId, trajectory);
        // InfoBox (dynamic)
        const description = new Cesium.CallbackProperty(time => {
            let closest = dataPoints[0], minDiff = Math.abs(Cesium.JulianDate.secondsDifference(time, closest.getTime()));
            for (const dp of dataPoints) {
                const diff = Math.abs(Cesium.JulianDate.secondsDifference(time, dp.getTime()));
                if (diff < minDiff) { closest = dp; minDiff = diff; }
            }
            return `
                <table style='font-size:15px; background:#222; color:#fff; border-collapse:collapse; min-width:220px;'>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Report Time</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.reportTimeDisplay}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Activity ID</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.mobileActivityId}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Status ID</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.mobileStatusId}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Altitude</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.posAlt}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Incline</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.plmInc}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>Payload</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.plmPayload}</td></tr>
                    <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>PLM State</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${closest.plmState}</td></tr>
                </table>
            `;
        }, false);
        const entity = this.vehicleDataSource.entities.add({
            name: unitId,
            position,
            orientation,
            model: this._createModelConfig(mobileTypeId),
            label: this._createLabelConfig(unitId, velocityProperty),
            description
        });
        if (mobileTypeId === 2) this._applyPayloadAndVesselTransform(entity, dataPoints);
        this.entities.set(unitId, entity);
        return entity;
    }

    _createPositionProperty(dataPoints) {
        const position = new Cesium.SampledPositionProperty();
        position.setInterpolationOptions({
            interpolationDegree: CONFIG.INTERPOLATION.DEGREE,
            interpolationAlgorithm: CONFIG.INTERPOLATION.ALGORITHM
        });
        let lastValidCartesian = null;
        for (const dp of dataPoints) {
            const cartesian = dp.getCartesian();
            if (dp.isStationary() && lastValidCartesian) {
                position.addSample(dp.getTime(), lastValidCartesian);
            } else {
                position.addSample(dp.getTime(), cartesian);
                lastValidCartesian = cartesian;
            }
        }
        return position;
    }

    _createOrientationProperty(dataPoints) {
        const orientation = new Cesium.SampledProperty(Cesium.Quaternion);
        orientation.setInterpolationOptions({
            interpolationDegree: CONFIG.INTERPOLATION.DEGREE,
            interpolationAlgorithm: CONFIG.INTERPOLATION.ALGORITHM
        });
        let lastValidQuaternion = null;
        for (const dp of dataPoints) {
            const cartesian = dp.getCartesian();
            const headingOffset = dp.getHeadingOffset();
            if (dp.isStationary() && lastValidQuaternion) {
                orientation.addSample(dp.getTime(), lastValidQuaternion);
                continue;
            }
            let heading = dp.heading + headingOffset;
            if (dp.isMovingBackward()) heading += 180;
            const headingRadians = Cesium.Math.toRadians(heading);
            const hpr = new Cesium.HeadingPitchRoll(headingRadians, 0, 0);
            const quaternion = Cesium.Transforms.headingPitchRollQuaternion(cartesian, hpr);
            orientation.addSample(dp.getTime(), quaternion);
            lastValidQuaternion = quaternion;
        }
        return orientation;
    }

    // Create model configuration for the vehicle
    _createModelConfig(mobileTypeId) {
        return {
            uri: mobileTypeId === 2 ? CONFIG.MODEL_PATHS.HD785 : CONFIG.MODEL_PATHS.EXCAVATOR,
            runAnimations: false
        };
    }

    // Create label configuration for the vehicle
    _createLabelConfig(unitId, velocityProperty) {
        const velocityVector = new Cesium.Cartesian3();
        return {
            text: new Cesium.CallbackProperty((time) => {
                velocityProperty.getValue(time, velocityVector);
                const mps = Cesium.Cartesian3.magnitude(velocityVector);
                const speedKph = mps * 3.6;
                return `${unitId}\n${speedKph < CONFIG.SPEED_THRESHOLD ? '0.0' : speedKph.toFixed(1)} kph`;
            }, false),
            font: CONFIG.LABEL.FONT,
            showBackground: true,
            distanceDisplayCondition: new Cesium.DistanceDisplayCondition(...CONFIG.LABEL.DISTANCE_RANGE),
            eyeOffset: new Cesium.Cartesian3(...CONFIG.LABEL.EYE_OFFSET)
        };
    }

    // Apply payload scaling and vessel rotation transformations
    _applyPayloadAndVesselTransform(entity, dataPoints) {
        const payloadScaling = this._getPayloadScaling(dataPoints);
        const vesselRotation = this._getVesselRotation(dataPoints);
        entity.model.nodeTransformations = {
            payload: {
                scale: payloadScaling.scale,
                rotation: vesselRotation.rotation
            },
            vessel: vesselRotation
        };
    }

    // Get payload scaling property
    _getPayloadScaling(dataPoints) {
        const scaleProperty = new Cesium.SampledProperty(Cesium.Cartesian3);
        for (const dp of dataPoints) {
            let scale = 1.0;
            if (!isNaN(dp.plmPayload) && dp.plmPayload > 0) {
                scale = dp.plmPayload / 100.0;
            }
            scaleProperty.addSample(dp.getTime(), new Cesium.Cartesian3(scale, scale, scale));
        }
        return {
            scale: new Cesium.CallbackProperty((time) => scaleProperty.getValue(time) || new Cesium.Cartesian3(1, 1, 1), false)
        };
    }

    // Get vessel rotation property
    _getVesselRotation(dataPoints) {
        const rotationProperty = new Cesium.SampledProperty(Cesium.Quaternion);
        for (const dp of dataPoints) {
            const angleDegrees = dp.vesselAngle || 0.0;
            const angleRadians = Cesium.Math.toRadians(angleDegrees);
            const quaternion = Cesium.Quaternion.fromAxisAngle(Cesium.Cartesian3.UNIT_X, angleRadians);
            rotationProperty.addSample(dp.getTime(), quaternion);
        }
        return {
            rotation: new Cesium.CallbackProperty((time) => rotationProperty.getValue(time) || Cesium.Quaternion.IDENTITY, false)
        };
    }

    showTrajectory(unitId) {
        // Hide all first
        for (const poly of this.trajectories.values()) poly.show = false;
        // Show only the selected
        if (this.trajectories.has(unitId)) this.trajectories.get(unitId).show = true;
    }

    hideAllTrajectories() {
        for (const poly of this.trajectories.values()) poly.show = false;
    }

    getAllEntities() {
        return Array.from(this.entities.values());
    }
}

// Timeline Manager: Handles Cesium timeline and animation settings
class TimelineManager {
    static configureTimeline(viewer, dataPoints) {
        const {start, end} = this._calculateTimeRange(dataPoints);
        viewer.clock.startTime = start.clone();
        viewer.clock.stopTime = end.clone();
        viewer.clock.currentTime = start.clone();
        viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
        viewer.clock.multiplier = CONFIG.TIMELINE.MULTIPLIER;
        viewer.timeline.zoomTo(start, end);
    }

    // Calculate the global time range for all data points
    static _calculateTimeRange(allDataPoints) {
        let globalStart = null, globalStop = null;
        for (const dp of allDataPoints) {
            const time = dp.getTime();
            if (!globalStart || time < globalStart) globalStart = time;
            if (!globalStop || time > globalStop) globalStop = time;
        }
        return {start: globalStart, end: globalStop};
    }
}

// Main Vehicle Visualization Manager
class VehicleVisualizationManager {
    constructor(viewer) {
        if (!viewer) {
            throw new Error("Viewer instance is required for VehicleVisualizationManager.");
        }
        this.viewer = viewer;
        this.entityManager = new VehicleEntityManager(this.viewer);
    }

    async initialize() {
        // Initializing Vehicle Visualization Manager
        try {
            const unitData = await CSVDataLoader.loadVehicleData();

            // Skip initialization if no vehicle data was loaded
            if (!unitData || Object.keys(unitData).length === 0) return;

            this._createVehicleEntities(unitData);
            this._configureTimeline(unitData);
            this._setupTrajectorySelection();
            this._setupSearchUI();
            
            // Vehicle entities created
        } catch (error) {
            console.error('Failed to initialize vehicle visualization:', error);
        }
    }

    // Create vehicle entities for all units
    _createVehicleEntities(unitData) {
        for (const [unitId, dataPoints] of Object.entries(unitData)) {
            dataPoints.sort((a, b) => new Date(a.reportTime) - new Date(b.reportTime));
            this.entityManager.createVehicle(unitId, dataPoints);
        }
    }

    // Configure the Cesium timeline for all data
    _configureTimeline(unitData) {
        const allDataPoints = Object.values(unitData).flat();
        TimelineManager.configureTimeline(this.viewer, allDataPoints);
        // Timeline configured
    }

    _setupTrajectorySelection() {
        this.viewer.selectedEntityChanged.addEventListener(selectedEntity => {
            this.entityManager.hideAllTrajectories();
            if (selectedEntity && this.entityManager.entities.has(selectedEntity.name)) {
                this.entityManager.showTrajectory(selectedEntity.name);
            }
        });
        // Trajectory selection event listener set up
    }

    getAllEntities() {
        return this.entityManager.getAllEntities();
    }

    // Search and focus on a vehicle by name
    searchAndFocusVehicle(name) {
        if (!name) return;
        const entity = this.entityManager.entities.get(name.toUpperCase());
        if (entity) {
            this.viewer.trackedEntity = entity;
            // Focused on vehicle
        } else {
            console.warn(`Vehicle with name "${name}" not found.`);
        }
    }

    // Add a simple search UI to the DOM
    _setupSearchUI() {
        const searchInput = document.getElementById('vehicle-search-input');
        const searchBtn = document.getElementById('vehicle-search-btn');
        if (searchInput && searchBtn) {
            const searchAction = () => {
                const query = searchInput.value.trim();
                this.searchAndFocusVehicle(query);
            };
            searchBtn.addEventListener('click', searchAction);
            searchInput.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') {
                    searchAction();
                }
            });
            // Vehicle search UI set up
        } else {
            console.warn('Vehicle search UI elements not found.');
        }
    }
}

// Main initialization function for the vehicle module
async function initializeVehicleVisualization(viewer) {
    if (!viewer) {
        console.error('Viewer is required for vehicle visualization.');
        return null;
    }
    const manager = new VehicleVisualizationManager(viewer);
    await manager.initialize();
    return manager;
}

export async function initialize(viewer) {
    return await initializeVehicleVisualization(viewer);
}
