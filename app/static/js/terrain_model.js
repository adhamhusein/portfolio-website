import {viewer} from './interface_model.js';
import { sessionManager } from './session_manager.js';

// Configuration
const CONFIG = {
    DATA_SOURCE: '/static/dataset/map_dataset_2.geojson', // Will be updated by session manager
    LABEL_ENABLED: true,
    CLUSTER_CONFIG: {
        enabled: true,
        pixelRange: 50,
        minimumSize: 3
    },
    LAYER_CONFIG: {
        dump: { color: Cesium.Color.BROWN, type: 'Polygon' },
        blast: { color: Cesium.Color.BLUE, type: 'Polygon' },
        road: { color: Cesium.Color.GRAY, type: 'LineString', width: 25 }
    },
    LABEL_STYLE: {
        font: 'bold 10pt sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 4,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundPadding: new Cesium.Cartesian2(7, 5)
    },
    HEATMAP_RANGES: {
        speed: { low: 18, medium: 21 },
        grade: { low: 2, medium: 4 },
        zeroSpeed: { low: 5, medium: 10 }
    },
    HEATMAP_COLORS: {
        speed: {
            low: Cesium.Color.RED,
            medium: Cesium.Color.YELLOW,
            high: Cesium.Color.GREEN,
            default: Cesium.Color.GRAY
        },
        grade: {
            low: Cesium.Color.GREEN,
            medium: Cesium.Color.YELLOW,
            high: Cesium.Color.RED,
            default: Cesium.Color.GRAY
        },
        zeroSpeed: {
            low: Cesium.Color.GREEN,
            medium: Cesium.Color.YELLOW,
            high: Cesium.Color.RED,
            default: Cesium.Color.GRAY
        }
    }
};

// Make CONFIG available globally for session manager
window.TERRAIN_CONFIG = CONFIG;

// State variables
let showSpeedHeatmap = false;
let showGradeHeatmap = false;
let showZeroSpeedHeatmap = false;

// Initialize clustering data source
export const customDataSource = new Cesium.CustomDataSource('ClusteredEntities');

document.addEventListener('viewerInitialized', () => {
    viewer.dataSources.add(customDataSource);
});

Object.assign(customDataSource.clustering, CONFIG.CLUSTER_CONFIG);

customDataSource.clustering.clusterEvent.addEventListener((clusteredEntities, cluster) => {
    const sampleText = clusteredEntities[0]?.name || 'Cluster';
    Object.assign(cluster.label, {
        ...CONFIG.LABEL_STYLE,
        text: sampleText,
        backgroundColor: Cesium.Color.YELLOW.withAlpha(0.5),
        show: CONFIG.LABEL_ENABLED
    });
});

// Utility functions
const calculateCentroid = coordinates => {
    const sum = coordinates.reduce((acc, coord) => [acc[0] + coord[0], acc[1] + coord[1]], [0, 0]);
    return [sum[0] / coordinates.length, sum[1] / coordinates.length];
};

const createDescription = (properties = {}) => {
    const fields = [
        { key: 'gid', label: 'gid' },
        { key: 'objectname', label: 'objectname' },
        { key: 'geom_type', label: 'geom_type' },
        { key: 'length', label: 'length' },
        { key: 'avg_speed', label: 'avg_speed' },
        { key: 'grade', label: 'grade' },
        { key: 'altitude', label: 'altitude' },
        { key: 'zero_speed', label: 'zero_speed' }
    ];
    return `
        <table style='font-size:15px; background:#222; color:#fff; border-collapse:collapse; min-width:220px;'>
            ${fields.map(f => `
                <tr><td style='font-weight:bold; padding:6px 12px; background:#333; border-right:1px solid #444; border-bottom:1px solid #444;'>${f.label}</td><td style='padding:6px 12px; background:#222; border-bottom:1px solid #444;'>${properties[f.key] !== undefined ? properties[f.key] : '-'}</td></tr>
            `).join('')}
        </table>
    `;
};

const createLabel = (name, position, backgroundColor = Cesium.Color.YELLOW.withAlpha(0.5), maxDistance = 5000) => ({
    text: name,
    position,
    show: CONFIG.LABEL_ENABLED,
    ...CONFIG.LABEL_STYLE,
    backgroundColor,
    heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
    distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, maxDistance)
});

// Color functions
const getSpeedColor = (speed) => {
    const colors = CONFIG.HEATMAP_COLORS.speed;
    const ranges = CONFIG.HEATMAP_RANGES.speed;
    if (speed < ranges.low) return colors.low;
    if (speed >= ranges.low && speed < ranges.medium) return colors.medium;
    if (speed >= ranges.medium) return colors.high;
    return colors.default;
};

const getGradeColor = (grade) => {
    const colors = CONFIG.HEATMAP_COLORS.grade;
    const ranges = CONFIG.HEATMAP_RANGES.grade;
    if (grade <= ranges.low) return colors.low;
    if (grade > ranges.low && grade <= ranges.medium) return colors.medium;
    if (grade > ranges.medium) return colors.high;
    return colors.default;
};

const getZeroSpeedColor = (zeroSpeed) => {
    const colors = CONFIG.HEATMAP_COLORS.zeroSpeed;
    const ranges = CONFIG.HEATMAP_RANGES.zeroSpeed;
    if (zeroSpeed < ranges.low) return colors.low;
    if (zeroSpeed >= ranges.low && zeroSpeed < ranges.medium) return colors.medium;
    if (zeroSpeed >= ranges.medium) return colors.high;
    return colors.default;
};

// Entity creation functions
export const createPolygon = (coordinates, color, name, properties = {}) => {
    const positions = coordinates.map(coord => Cesium.Cartesian3.fromDegrees(coord[0], coord[1]));
    const [avgLon, avgLat] = calculateCentroid(coordinates);
    const labelPosition = Cesium.Cartesian3.fromDegrees(avgLon, avgLat);

    return customDataSource.entities.add({
        name,
        polygon: {
            hierarchy: new Cesium.PolygonHierarchy(positions),
            material: color.withAlpha(0.5),
            outline: true,
            outlineColor: Cesium.Color.BLACK,
            height: 0,
            heightReference: Cesium.HeightReference.NONE,
            perPositionHeight: false
        },
        position: labelPosition,
        label: createLabel(name, labelPosition),
        description: new Cesium.ConstantProperty(createDescription(properties))
    });
};

export const createCorridor = (coordinates, width, color, name, speedTarget = 0, properties = {}) => {
    const positions = coordinates.map(coord => Cesium.Cartesian3.fromDegrees(coord[0], coord[1]));
    const midCoord = coordinates[Math.floor(coordinates.length / 2)];
    const labelPosition = Cesium.Cartesian3.fromDegrees(midCoord[0], midCoord[1]);

    const entity = customDataSource.entities.add({
        name,
        corridor: {
            positions,
            width,
            material: Cesium.Color.GRAY.withAlpha(0.7),
            height: 0,
            extrudedHeight: 0,
            heightReference: Cesium.HeightReference.NONE
        },
        position: labelPosition,
        label: createLabel(name, labelPosition, Cesium.Color.BLACK.withAlpha(0.3), 500),
        description: new Cesium.ConstantProperty(createDescription(properties))
    });

    entity.properties = properties;
    return entity;
};

// Feature processing
export const processFeatures = (data, config) => {
    data.features?.forEach(feature => {
        const name = feature.properties?.objectname || 'Unnamed';
        const speedTarget = feature.properties?.speed_travel_max_target || 0;
        const { geometry, properties } = feature;
        
        if (!geometry?.coordinates) return;

        if (geometry.type === 'Polygon') {
            createPolygon(geometry.coordinates[0], config.color, name, properties);
        } else if (geometry.type === 'LineString') {
            createCorridor(geometry.coordinates, config.width, config.color, name, speedTarget, properties);
        }
    });
};

// Main loading function
export const loadGeoJSON = async () => {
    try {
        // Initialize session manager and update data source
        sessionManager.initialize();

        // Skip loading if no real session data (default sample files don't exist)
        if (!sessionManager.hasDataFiles()) return null;

        CONFIG.DATA_SOURCE = sessionManager.getGeoJsonDataUrl();
        
        const response = await fetch(CONFIG.DATA_SOURCE);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        data.features?.forEach(feature => {
            const geomType = feature.properties?.geom_type;
            let key;
            if (geomType === 'front') key = 'blast';
            else if (geomType === 'disposal') key = 'dump';
            else if (geomType === 'road') key = 'road';
            else return;
            const config = CONFIG.LAYER_CONFIG[key];
            processFeatures({ features: [feature] }, config);
        });

        // GeoJSON layer loaded
        updateCorridorColors();
        return data; // Return the data for promise resolution
    } catch (error) {
        console.error('Failed to load GeoJSON data:', error);
        throw error; // Re-throw for promise rejection
    }
};

// Update functions
export const updateCorridorColors = () => {
    customDataSource.entities.values.forEach(entity => {
        if (entity.corridor && entity.properties) {
            let color;
            if (showSpeedHeatmap) {
                const speed = entity.properties.avg_speed;
                color = speed !== undefined ? getSpeedColor(speed) : Cesium.Color.GRAY;
            } else if (showGradeHeatmap) {
                const grade = entity.properties.grade;
                color = grade !== undefined ? getGradeColor(grade) : Cesium.Color.GRAY;
            } else if (showZeroSpeedHeatmap) {
                const zeroSpeed = entity.properties.zero_speed;
                color = zeroSpeed !== undefined ? getZeroSpeedColor(zeroSpeed) : Cesium.Color.GRAY;
            } else {
                color = Cesium.Color.GRAY;
            }
            entity.corridor.material = color.withAlpha(0.7);
        }
    });
    generateLegend();
};

export const updateLabelsVisibility = () => {
    customDataSource.entities.values.forEach(entity => {
        if (entity.label) {
            entity.label.show = CONFIG.LABEL_ENABLED;
        }
    });
    
    if (customDataSource.clustering) {
        customDataSource.clustering.clusterEvent.raiseEvent();
    }
};

// Legend generation
const generateLegend = () => {
    const legendContent = document.getElementById('legend-content');
    if (!showSpeedHeatmap && !showGradeHeatmap && !showZeroSpeedHeatmap) {
        legendContent.innerHTML = 'No heatmap active';
        return;
    }

    let legendHTML = '';
    
    if (showSpeedHeatmap) {
        const colors = CONFIG.HEATMAP_COLORS.speed;
        const ranges = CONFIG.HEATMAP_RANGES.speed;
        legendHTML = `
            <div style="margin-bottom: 4px; font-weight: bold;">Speed Heatmap</div>
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.low.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&lt;${ranges.low}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.medium.toCssColorString()};"></div>
                    <span style="font-size: 10px;">${ranges.low}-${ranges.medium}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.high.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&gt;${ranges.medium}</span>
                </div>
            </div>
        `;
    } else if (showGradeHeatmap) {
        const colors = CONFIG.HEATMAP_COLORS.grade;
        const ranges = CONFIG.HEATMAP_RANGES.grade;
        legendHTML = `
            <div style="margin-bottom: 4px; font-weight: bold;">Grade Heatmap</div>
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.low.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&lt;${ranges.low}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.medium.toCssColorString()};"></div>
                    <span style="font-size: 10px;">${ranges.low}-${ranges.medium}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.high.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&gt;${ranges.medium}</span>
                </div>
            </div>
        `;
    } else if (showZeroSpeedHeatmap) {
        const colors = CONFIG.HEATMAP_COLORS.zeroSpeed;
        const ranges = CONFIG.HEATMAP_RANGES.zeroSpeed;
        legendHTML = `
            <div style="margin-bottom: 4px; font-weight: bold;">Zero Speed Heatmap</div>
            <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.low.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&lt;${ranges.low}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.medium.toCssColorString()};"></div>
                    <span style="font-size: 10px;">${ranges.low}-${ranges.medium}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2px;">
                    <div style="width: 16px; height: 10px; background: ${colors.high.toCssColorString()};"></div>
                    <span style="font-size: 10px;">&gt;${ranges.medium}</span>
                </div>
            </div>
        `;
    }
    
    legendContent.innerHTML = legendHTML;
};

// Event listeners
export const initializeHeatmapControls = () => {
    const speedToggle = document.getElementById('speed-heatmap-toggle');
    const gradeToggle = document.getElementById('grade-heatmap-toggle');
    const zeroSpeedToggle = document.getElementById('zero-speed-heatmap-toggle');
    const labelToggle = document.getElementById('label-toggle');
    
    const speedLowMax = document.getElementById('speed-low-max');
    const speedMediumMax = document.getElementById('speed-medium-max');
    const gradeLowMax = document.getElementById('grade-low-max');
    const gradeMediumMax = document.getElementById('grade-medium-max');
    const zeroSpeedLowMax = document.getElementById('zero-speed-low-max');
    const zeroSpeedMediumMax = document.getElementById('zero-speed-medium-max');

    if (speedToggle && gradeToggle && zeroSpeedToggle && labelToggle) {
        speedToggle.addEventListener('change', () => {
            showSpeedHeatmap = speedToggle.checked;
            if (showSpeedHeatmap) {
                showGradeHeatmap = false;
                gradeToggle.checked = false;
                showZeroSpeedHeatmap = false;
                zeroSpeedToggle.checked = false;
            }
            updateCorridorColors();
        });

        gradeToggle.addEventListener('change', () => {
            showGradeHeatmap = gradeToggle.checked;
            if (showGradeHeatmap) {
                showSpeedHeatmap = false;
                speedToggle.checked = false;
                showZeroSpeedHeatmap = false;
                zeroSpeedToggle.checked = false;
            }
            updateCorridorColors();
        });

        zeroSpeedToggle.addEventListener('change', () => {
            showZeroSpeedHeatmap = zeroSpeedToggle.checked;
            if (showZeroSpeedHeatmap) {
                showSpeedHeatmap = false;
                showGradeHeatmap = false;
                speedToggle.checked = false;
                gradeToggle.checked = false;
            }
            updateCorridorColors();
        });

        labelToggle.addEventListener('change', () => {
            CONFIG.LABEL_ENABLED = labelToggle.checked;
            updateLabelsVisibility();
        });
    }

    if (speedLowMax) {
        speedLowMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.speed.low = parseFloat(speedLowMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.speed.low >= CONFIG.HEATMAP_RANGES.speed.medium) {
                CONFIG.HEATMAP_RANGES.speed.medium = CONFIG.HEATMAP_RANGES.speed.low + 1;
                speedMediumMax.value = CONFIG.HEATMAP_RANGES.speed.medium;
            }
            updateCorridorColors();
        });
    }

    if (speedMediumMax) {
        speedMediumMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.speed.medium = parseFloat(speedMediumMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.speed.medium <= CONFIG.HEATMAP_RANGES.speed.low) {
                CONFIG.HEATMAP_RANGES.speed.low = CONFIG.HEATMAP_RANGES.speed.medium - 1;
                speedLowMax.value = CONFIG.HEATMAP_RANGES.speed.low;
            }
            updateCorridorColors();
        });
    }

    if (gradeLowMax) {
        gradeLowMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.grade.low = parseFloat(gradeLowMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.grade.low >= CONFIG.HEATMAP_RANGES.grade.medium) {
                CONFIG.HEATMAP_RANGES.grade.medium = CONFIG.HEATMAP_RANGES.grade.low + 1;
                gradeMediumMax.value = CONFIG.HEATMAP_RANGES.grade.medium;
            }
            updateCorridorColors();
        });
    }

    if (gradeMediumMax) {
        gradeMediumMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.grade.medium = parseFloat(gradeMediumMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.grade.medium <= CONFIG.HEATMAP_RANGES.grade.low) {
                CONFIG.HEATMAP_RANGES.grade.low = CONFIG.HEATMAP_RANGES.grade.medium - 1;
                gradeLowMax.value = CONFIG.HEATMAP_RANGES.grade.low;
            }
            updateCorridorColors();
        });
    }

    if (zeroSpeedLowMax) {
        zeroSpeedLowMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.zeroSpeed.low = parseFloat(zeroSpeedLowMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.zeroSpeed.low >= CONFIG.HEATMAP_RANGES.zeroSpeed.medium) {
                CONFIG.HEATMAP_RANGES.zeroSpeed.medium = CONFIG.HEATMAP_RANGES.zeroSpeed.low + 1;
                zeroSpeedMediumMax.value = CONFIG.HEATMAP_RANGES.zeroSpeed.medium;
            }
            updateCorridorColors();
        });
    }

    if (zeroSpeedMediumMax) {
        zeroSpeedMediumMax.addEventListener('input', () => {
            CONFIG.HEATMAP_RANGES.zeroSpeed.medium = parseFloat(zeroSpeedMediumMax.value) || 0;
            if (CONFIG.HEATMAP_RANGES.zeroSpeed.medium <= CONFIG.HEATMAP_RANGES.zeroSpeed.low) {
                CONFIG.HEATMAP_RANGES.zeroSpeed.low = CONFIG.HEATMAP_RANGES.zeroSpeed.medium - 1;
                zeroSpeedLowMax.value = CONFIG.HEATMAP_RANGES.zeroSpeed.low;
            }
            updateCorridorColors();
        });
    }
};

// Initialization is handled by cesium_main.js after viewer is ready
