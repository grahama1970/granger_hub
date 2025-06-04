"""
Time Series Forecast Visualization using D3.js.

Integrates with the arangodb D3 visualization engine to create interactive
time series forecast visualizations with confidence intervals.

Sample usage:
    visualizer = ForecastVisualizer()
    html = visualizer.create_forecast_graph(historical_data, predictions, intervals)
    visualizer.save_to_file(html, "forecast.html")
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
from datetime import datetime, timedelta
import logging

# Add arangodb visualization to path
ARANGODB_PATH = Path("/home/graham/workspace/experiments/arangodb")
if str(ARANGODB_PATH) not in sys.path:
    sys.path.insert(0, str(ARANGODB_PATH))

try:
    from src.arangodb.visualization.core.d3_engine import D3VisualizationEngine, VisualizationConfig
    D3_AVAILABLE = True
except ImportError:
    D3_AVAILABLE = False
    logging.warning("D3 visualization engine not available. Install arangodb package.")

logger = logging.getLogger(__name__)


class ForecastVisualizer:
    """Creates D3.js visualizations for time series forecasts."""
    
    def __init__(self, use_d3_engine: bool = True):
        """
        Initialize the forecast visualizer.
        
        Args:
            use_d3_engine: Whether to use the arangodb D3 engine
        """
        self.use_d3_engine = use_d3_engine and D3_AVAILABLE
        
        if self.use_d3_engine:
            self.d3_engine = D3VisualizationEngine(use_llm=False, optimize_performance=False)
    
    def create_forecast_graph(
        self,
        historical_data: np.ndarray,
        predictions: np.ndarray,
        confidence_intervals: Optional[Dict[float, Tuple[np.ndarray, np.ndarray]]] = None,
        timestamps: Optional[List[datetime]] = None,
        title: str = "Time Series Forecast",
        width: int = 1200,
        height: int = 600
    ) -> str:
        """
        Create an interactive D3.js visualization of the forecast.
        
        Args:
            historical_data: Historical time series values
            predictions: Forecasted values
            confidence_intervals: Dict of confidence levels to (lower, upper) bounds
            timestamps: Optional timestamps for x-axis
            title: Chart title
            width: Chart width in pixels
            height: Chart height in pixels
            
        Returns:
            HTML string containing the complete visualization
        """
        if self.use_d3_engine:
            # Convert to graph format for D3 engine
            graph_data = self._convert_to_graph_format(
                historical_data, predictions, confidence_intervals, timestamps
            )
            
            # Create custom config for time series
            config = VisualizationConfig(
                width=width,
                height=height,
                layout="custom",  # We'll use custom D3 code
                title=title,
                custom_settings={
                    "chart_type": "time_series",
                    "show_grid": True,
                    "show_axes": True,
                    "animate_path": True
                }
            )
            
            # Generate using custom template
            return self._generate_custom_timeseries_html(
                graph_data, config, title
            )
        else:
            # Fallback to simple HTML/JS visualization
            return self._generate_simple_visualization(
                historical_data, predictions, confidence_intervals, timestamps, title
            )
    
    def _convert_to_graph_format(
        self,
        historical_data: np.ndarray,
        predictions: np.ndarray,
        confidence_intervals: Optional[Dict],
        timestamps: Optional[List[datetime]]
    ) -> Dict[str, Any]:
        """Convert time series data to graph format for D3 engine."""
        # Generate timestamps if not provided
        if timestamps is None:
            total_points = len(historical_data) + len(predictions)
            timestamps = [datetime.now() + timedelta(hours=i) for i in range(total_points)]
        
        # Create nodes representing data points
        nodes = []
        links = []
        
        # Historical data points
        for i, (ts, value) in enumerate(zip(timestamps[:len(historical_data)], historical_data)):
            nodes.append({
                "id": f"hist_{i}",
                "timestamp": ts.isoformat(),
                "value": float(value),
                "type": "historical",
                "index": i
            })
        
        # Prediction data points
        pred_start = len(historical_data)
        for i, (ts, value) in enumerate(zip(timestamps[pred_start:], predictions)):
            node_id = f"pred_{i}"
            nodes.append({
                "id": node_id,
                "timestamp": ts.isoformat(),
                "value": float(value),
                "type": "prediction",
                "index": pred_start + i
            })
            
            # Add confidence intervals if available
            if confidence_intervals:
                for level, (lower, upper) in confidence_intervals.items():
                    nodes[-1][f"ci_{int(level*100)}_lower"] = float(lower[i])
                    nodes[-1][f"ci_{int(level*100)}_upper"] = float(upper[i])
        
        # Create links to show continuity
        for i in range(len(nodes) - 1):
            links.append({
                "source": nodes[i]["id"],
                "target": nodes[i + 1]["id"],
                "value": 1
            })
        
        return {
            "nodes": nodes,
            "links": links,
            "metadata": {
                "type": "time_series_forecast",
                "historical_count": len(historical_data),
                "prediction_count": len(predictions),
                "has_confidence_intervals": confidence_intervals is not None
            }
        }
    
    def _generate_custom_timeseries_html(
        self,
        graph_data: Dict[str, Any],
        config: VisualizationConfig,
        title: str
    ) -> str:
        """Generate custom HTML for time series visualization."""
        
        # Custom D3 script for time series
        d3_script = """
        // Set dimensions and margins
        const margin = {top: 20, right: 80, bottom: 50, left: 70};
        const width = """ + str(config.width) + """ - margin.left - margin.right;
        const height = """ + str(config.height) + """ - margin.top - margin.bottom;
        
        // Parse the data
        const data = graphData.nodes;
        const historicalData = data.filter(d => d.type === 'historical');
        const predictionData = data.filter(d => d.type === 'prediction');
        
        // Set up scales
        const parseTime = d3.timeParse("%Y-%m-%dT%H:%M:%S");
        data.forEach(d => {
            d.date = parseTime(d.timestamp.split('.')[0]);
        });
        
        const xScale = d3.scaleTime()
            .domain(d3.extent(data, d => d.date))
            .range([0, width]);
            
        const yScale = d3.scaleLinear()
            .domain([
                d3.min(data, d => d.value) * 0.9,
                d3.max(data, d => d.value) * 1.1
            ])
            .range([height, 0]);
        
        // Create SVG
        const svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
        
        // Add axes
        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%m/%d %H:%M")));
            
        svg.append("g")
            .call(d3.axisLeft(yScale));
        
        // Add axis labels
        svg.append("text")
            .attr("transform", "rotate(-90)")
            .attr("y", 0 - margin.left)
            .attr("x", 0 - (height / 2))
            .attr("dy", "1em")
            .style("text-anchor", "middle")
            .text("Value");
            
        svg.append("text")
            .attr("transform", `translate(${width / 2}, ${height + margin.bottom})`)
            .style("text-anchor", "middle")
            .text("Time");
        
        // Line generator
        const line = d3.line()
            .x(d => xScale(d.date))
            .y(d => yScale(d.value))
            .curve(d3.curveMonotoneX);
        
        // Draw historical line
        svg.append("path")
            .datum(historicalData)
            .attr("fill", "none")
            .attr("stroke", "steelblue")
            .attr("stroke-width", 2)
            .attr("d", line)
            .attr("class", "historical-line");
        
        // Draw prediction line
        svg.append("path")
            .datum(predictionData)
            .attr("fill", "none")
            .attr("stroke", "red")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5")
            .attr("d", line)
            .attr("class", "prediction-line");
        
        // Draw confidence intervals if available
        const hasCI = predictionData.length > 0 && predictionData[0].ci_90_lower !== undefined;
        
        if (hasCI) {
            // 90% confidence interval
            const area90 = d3.area()
                .x(d => xScale(d.date))
                .y0(d => yScale(d.ci_90_lower))
                .y1(d => yScale(d.ci_90_upper))
                .curve(d3.curveMonotoneX);
                
            svg.append("path")
                .datum(predictionData)
                .attr("fill", "red")
                .attr("fill-opacity", 0.1)
                .attr("d", area90);
                
            // 50% confidence interval if available
            if (predictionData[0].ci_50_lower !== undefined) {
                const area50 = d3.area()
                    .x(d => xScale(d.date))
                    .y0(d => yScale(d.ci_50_lower))
                    .y1(d => yScale(d.ci_50_upper))
                    .curve(d3.curveMonotoneX);
                    
                svg.append("path")
                    .datum(predictionData)
                    .attr("fill", "red")
                    .attr("fill-opacity", 0.2)
                    .attr("d", area50);
            }
        }
        
        // Add connecting line between historical and prediction
        if (historicalData.length > 0 && predictionData.length > 0) {
            const connectionData = [
                historicalData[historicalData.length - 1],
                predictionData[0]
            ];
            
            svg.append("path")
                .datum(connectionData)
                .attr("fill", "none")
                .attr("stroke", "gray")
                .attr("stroke-width", 1)
                .attr("stroke-dasharray", "2,2")
                .attr("d", line);
        }
        
        // Add legend
        const legend = svg.append("g")
            .attr("transform", `translate(${width - 120}, 20)`);
            
        legend.append("line")
            .attr("x1", 0).attr("x2", 20)
            .attr("y1", 0).attr("y2", 0)
            .style("stroke", "steelblue")
            .style("stroke-width", 2);
        legend.append("text")
            .attr("x", 25).attr("y", 5)
            .text("Historical");
            
        legend.append("line")
            .attr("x1", 0).attr("x2", 20)
            .attr("y1", 20).attr("y2", 20)
            .style("stroke", "red")
            .style("stroke-width", 2)
            .style("stroke-dasharray", "5,5");
        legend.append("text")
            .attr("x", 25).attr("y", 25)
            .text("Forecast");
            
        if (hasCI) {
            legend.append("rect")
                .attr("x", 0).attr("y", 35)
                .attr("width", 20).attr("height", 10)
                .style("fill", "red")
                .style("fill-opacity", 0.2);
            legend.append("text")
                .attr("x", 25).attr("y", 45)
                .text("Confidence");
        }
        
        // Add interactivity
        const tooltip = d3.select("#tooltip");
        
        // Add dots for data points
        svg.selectAll(".dot")
            .data(data)
            .enter().append("circle")
            .attr("class", "dot")
            .attr("cx", d => xScale(d.date))
            .attr("cy", d => yScale(d.value))
            .attr("r", 3)
            .attr("fill", d => d.type === "historical" ? "steelblue" : "red")
            .on("mouseover", function(event, d) {
                tooltip.style("opacity", 1)
                    .html(`<strong>${d.type === "historical" ? "Historical" : "Forecast"}</strong><br/>
                           Time: ${d3.timeFormat("%m/%d %H:%M")(d.date)}<br/>
                           Value: ${d.value.toFixed(4)}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", function() {
                tooltip.style("opacity", 0);
            });
        
        // Remove loading indicator
        d3.select(".loading").remove();
        """
        
        # Generate HTML
        html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        #graph-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 0 auto;
            max-width: {width}px;
        }}
        
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
        }}
        
        .tooltip {{
            position: absolute;
            padding: 10px;
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }}
        
        .loading {{
            text-align: center;
            padding: 50px;
            color: #666;
        }}
        
        .dot {{
            cursor: pointer;
        }}
        
        .dot:hover {{
            r: 5;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div id="graph-container">
        <div class="loading">Loading visualization...</div>
    </div>
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        const graphData = {graph_data};
        {d3_script}
    </script>
</body>
</html>"""
        
        return html_template.format(
            title=title,
            width=config.width + 40,
            graph_data=json.dumps(graph_data),
            d3_script=d3_script
        )
    
    def _generate_simple_visualization(
        self,
        historical_data: np.ndarray,
        predictions: np.ndarray,
        confidence_intervals: Optional[Dict],
        timestamps: Optional[List[datetime]],
        title: str
    ) -> str:
        """Generate a simple fallback visualization without D3 engine."""
        # Simple HTML with inline chart using Chart.js as fallback
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>{title}</h1>
    <canvas id="chart"></canvas>
    <script>
        // Chart.js implementation here
        console.log("Simple visualization not fully implemented");
    </script>
</body>
</html>"""
    
    def save_to_file(self, html_content: str, filename: str):
        """Save the visualization HTML to a file."""
        filepath = Path(filename)
        filepath.write_text(html_content, encoding='utf-8')
        logger.info(f"Visualization saved to {filepath.absolute()}")
    
    def serve_visualization(self, html_content: str, port: int = 8888):
        """Serve the visualization on a local HTTP server."""
        import tempfile
        import webbrowser
        import http.server
        import socketserver
        import threading
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_content)
            temp_path = f.name
        
        # Start simple HTTP server
        Handler = http.server.SimpleHTTPRequestHandler
        
        def serve():
            with socketserver.TCPServer(("", port), Handler) as httpd:
                print(f"Serving at http://localhost:{port}/{Path(temp_path).name}")
                httpd.serve_forever()
        
        # Start server in background
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        
        # Open browser
        webbrowser.open(f"http://localhost:{port}/{Path(temp_path).name}")


# Validation
if __name__ == "__main__":
    # Test the visualization
    import numpy as np
    
    # Generate sample data
    t = np.linspace(0, 100, 200)
    historical = np.sin(0.1 * t) + 0.1 * np.random.randn(200)
    predictions = np.sin(0.1 * np.arange(100, 124)) + 0.05
    
    # Create confidence intervals
    intervals = {
        0.5: (predictions - 0.1, predictions + 0.1),
        0.9: (predictions - 0.2, predictions + 0.2)
    }
    
    # Create visualizer
    viz = ForecastVisualizer()
    html = viz.create_forecast_graph(
        historical[-100:],  # Last 100 points
        predictions,
        intervals,
        title="Time Series Forecast Example"
    )
    
    # Save and display
    viz.save_to_file(html, "forecast_example.html")
    print("Visualization saved to forecast_example.html")