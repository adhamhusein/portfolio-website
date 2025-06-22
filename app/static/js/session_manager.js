// Session Manager for Project 004
// Handles session-based data loading and configuration

class SessionManager {
    constructor() {
        this.sessionData = null;
        this.isInitialized = false;
    }

    // Initialize session data from URL parameters or sessionStorage
    initialize() {
        if (this.isInitialized) return this.sessionData;

        // Try to get session data from URL parameters first
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session_id');

        if (sessionId) {
            // Try to get session data from sessionStorage
            const storedData = sessionStorage.getItem('project004_session');
            if (storedData) {
                try {
                    this.sessionData = JSON.parse(storedData);
                    this.isInitialized = true;
                    console.log('Session initialized from storage:', this.sessionData);
                    return this.sessionData;
                } catch (error) {
                    console.error('Error parsing session data:', error);
                }
            }
        }

        // Fallback to default data sources
        this.sessionData = {
            session_id: 'default',
            processed_files: {
                position_processed: '/static/dataset/datasheet12.csv',
                geojson: '/static/dataset/map_dataset_2.geojson'
            },
            processing_info: {
                processed_at: new Date().toISOString(),
                vehicle_data_rows: 0
            }
        };
        this.isInitialized = true;
        console.log('Using default session data:', this.sessionData);
        return this.sessionData;
    }

    // Get the processed position data URL
    getPositionDataUrl() {
        if (!this.isInitialized) this.initialize();
        
        const filename = this.sessionData.processed_files.position_processed;
        if (filename.startsWith('/')) {
            return filename; // Absolute path
        } else {
            return `/project/project_004_processed/${filename}`;
        }
    }

    // Get the processed GeoJSON data URL
    getGeoJsonDataUrl() {
        if (!this.isInitialized) this.initialize();
        
        const filename = this.sessionData.processed_files.geojson;
        if (filename.startsWith('/')) {
            return filename; // Absolute path
        } else {
            return `/project/project_004_processed/${filename}`;
        }
    }

    // Get session ID
    getSessionId() {
        if (!this.isInitialized) this.initialize();
        return this.sessionData.session_id;
    }

    // Get processing info
    getProcessingInfo() {
        if (!this.isInitialized) this.initialize();
        return this.sessionData.processing_info;
    }

    // Check if using session data vs default data
    isUsingSessionData() {
        if (!this.isInitialized) this.initialize();
        return this.sessionData.session_id !== 'default';
    }

    // Update configuration objects with session data
    updateConfigs() {
        if (!this.isInitialized) this.initialize();
        
        // Update terrain model config
        if (window.TERRAIN_CONFIG) {
            window.TERRAIN_CONFIG.DATA_SOURCE = this.getGeoJsonDataUrl();
        }
        
        // Update vehicle model config
        if (window.VEHICLE_CONFIG) {
            window.VEHICLE_CONFIG.CSV.DATA_PATH = this.getPositionDataUrl();
        }
        
        console.log('Configs updated with session data');
    }
}

// Create global instance
const sessionManager = new SessionManager();

// Export for use in other modules
export { sessionManager };
export default sessionManager; 