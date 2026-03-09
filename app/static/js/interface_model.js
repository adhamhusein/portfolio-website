Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlZGNlYjExZS1jNWRjLTQ4NWMtOTVhNi0zMTU0ZjYzYTk2NjUiLCJpZCI6MzA5NTI4LCJpYXQiOjE3NDkxMjA1Nzh9._Oe8mDxZeXPGXYn_4tJpMGhn3n9ZY1IsdBYJKaQ1af8';

export let viewer;

document.addEventListener('DOMContentLoaded', () => {
    viewer = new Cesium.Viewer('cesiumContainer', {
        navigationHelpButton: false,
        shouldAnimate: true,
        infoBox: true,
        timeline: true,
        animation: true,
    });

    // Dispatch a custom event to signal that the viewer is ready
    const event = new Event('viewerInitialized');
    document.dispatchEvent(event);
});