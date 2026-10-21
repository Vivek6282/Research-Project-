/**
 * Trackside Visualizer — Start-up.
 * Draws the empty g chart and connects to the simulator's WebSocket once all other scripts are loaded.
 * (Runs are started from the Coach screen: Maps & Demo > Play demo; this page only watches.)
 */

(function () {
  if (window.TracksideChart && window.TracksideStream) {
    window.TracksideChart.drawChart(window.TracksideStream.canvas, window.TracksideStream.ctx, 1.15);
    window.TracksideStream.connectWebSocket();
  }
})();
