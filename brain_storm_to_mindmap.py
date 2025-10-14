"""
Brainstorming Results to Mindmap Visualizer

This script takes brainstorming results (from TinyTroupe or other sources) and generates
a visual mindmap representation. The mindmap can be exported as an image file.

As per my primary guidelines, this implementation is kept elegant and concise while 
remaining readable and maintainable.
"""

import json
from pathlib import Path
from typing import Dict, List, Union, Tuple
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap
from dotenv import load_dotenv
import math

load_dotenv()  # Load environment variables from .env file if present


class BrainstormingMindmap:
    """
    Creates a visual mindmap from brainstorming results.
    
    This class takes structured brainstorming data and generates a mindmap
    visualization using matplotlib, with customizable colors and styles.
    """
    
    def __init__(self, title: str = "Brainstorming Results"):
        """
        Initialize the mindmap generator.
        
        Args:
            title: The main title for the mindmap
        """
        self.title = title
        self.fig = None
        self.ax = None
        self.placed_nodes = []  # Track placed nodes for collision detection
        
        # Visual configuration
        self.colors = {
            'central': '#FF6B6B',      # Red for central topic
            'main_idea': '#4ECDC4',    # Teal for main ideas
            'detail': '#95E1D3',       # Light teal for details
            'background': '#F8F9FA',   # Light gray background
            'text': '#2C3E50'          # Dark blue-gray for text
        }
        
    def create_from_extraction(self, extraction_result: Union[str, Dict, List]) -> None:
        """
        Create a mindmap from TinyTroupe extraction results.
        
        Args:
            extraction_result: Can be a JSON string, dict, or list of ideas
        """
        # Parse input if it's a string
        if isinstance(extraction_result, str):
            try:
                extraction_result = json.loads(extraction_result)
            except json.JSONDecodeError:
                # Try to parse as simple list
                extraction_result = [item.strip() for item in extraction_result.split('\n') if item.strip()]
        
        # Convert to standard format
        if isinstance(extraction_result, list):
            ideas = self._parse_list_format(extraction_result)
        elif isinstance(extraction_result, dict):
            ideas = self._parse_dict_format(extraction_result)
        else:
            raise ValueError("Extraction result must be a string, dict, or list")
        
        self._create_mindmap(ideas)
    
    def _parse_list_format(self, items: List) -> List[Dict]:
        """Parse a simple list of items into structured ideas."""
        ideas = []
        for i, item in enumerate(items, 1):
            if isinstance(item, str):
                ideas.append({
                    'title': f'Idea {i}',
                    'description': item,
                    'details': []
                })
            elif isinstance(item, dict):
                ideas.append(item)
        return ideas
    
    def _parse_dict_format(self, data: Dict) -> List[Dict]:
        """Parse dictionary format extraction results."""
        # Handle different possible dictionary structures
        if 'ideas' in data:
            return data['ideas']
        elif 'results' in data:
            return data['results']
        else:
            # Assume the dict itself represents ideas
            return [data]
    
    def _create_mindmap(self, ideas: List[Dict]) -> None:
        """
        Create the actual mindmap visualization.
        
        Args:
            ideas: List of idea dictionaries with title, description, and optionally details
        """
        # Set up the figure
        self.fig, self.ax = plt.subplots(figsize=(16, 12))
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-8, 8)
        self.ax.axis('off')
        self.fig.patch.set_facecolor(self.colors['background'])
        
        # Reset placed nodes
        self.placed_nodes = []
        
        # Draw central topic
        central_box = {'x': 0, 'y': 0, 'width': 3, 'height': 1}
        self.placed_nodes.append(central_box)
        self._draw_central_node(self.title)
        
        # Calculate positions for ideas with collision avoidance
        n_ideas = len(ideas)
        if n_ideas == 0:
            return
        
        # Use adaptive radius based on number of ideas
        base_radius = max(5, 3 + n_ideas * 0.3)
        angle_step = 2 * math.pi / n_ideas
        
        for i, idea in enumerate(ideas):
            # Calculate initial position
            angle = i * angle_step
            position = self._find_non_overlapping_position(angle, base_radius, idea)
            
            if position:
                x, y, box_width, box_height = position
                self._draw_idea_node(idea, x, y, angle)
                self._draw_connection((0, 0), (x, y))
    
    def _calculate_box_dimensions(self, idea: Dict) -> Tuple[float, float]:
        """Calculate the dimensions needed for an idea box."""
        description = idea.get('description', '')
        wrapped_desc = self._wrap_text(description, 30)
        
        box_width = 2.5
        box_height = 1.2 + len(wrapped_desc.split('\n')) * 0.15
        
        return box_width, box_height
    
    def _find_non_overlapping_position(self, angle: float, base_radius: float, 
                                       idea: Dict) -> Tuple[float, float, float, float]:
        """
        Find a position for a node that doesn't overlap with existing nodes.
        
        Args:
            angle: Preferred angle for placement
            base_radius: Base distance from center
            idea: Idea dictionary to calculate box size
            
        Returns:
            Tuple of (x, y, width, height) or None if no position found
        """
        box_width, box_height = self._calculate_box_dimensions(idea)
        
        # Try increasing radii until we find a spot
        max_attempts = 10
        for attempt in range(max_attempts):
            radius = base_radius + attempt * 0.8
            
            # Try the preferred angle first
            angles_to_try = [angle]
            
            # If that doesn't work, try nearby angles
            if attempt > 0:
                angle_offset = (attempt * 0.3)
                angles_to_try.extend([
                    angle + angle_offset,
                    angle - angle_offset,
                ])
            
            for try_angle in angles_to_try:
                x = radius * math.cos(try_angle)
                y = radius * math.sin(try_angle)
                
                # Check for overlaps
                new_box = {
                    'x': x,
                    'y': y,
                    'width': box_width,
                    'height': box_height
                }
                
                if not self._has_overlap(new_box):
                    self.placed_nodes.append(new_box)
                    return x, y, box_width, box_height
        
        # Fallback: place it anyway but log warning
        x = base_radius * math.cos(angle)
        y = base_radius * math.sin(angle)
        print("Warning: Could not find non-overlapping position for idea, using fallback position")
        return x, y, box_width, box_height
    
    def _has_overlap(self, box: Dict, margin: float = 0.5) -> bool:
        """
        Check if a box overlaps with any placed nodes.
        
        Args:
            box: Dictionary with x, y, width, height
            margin: Additional spacing margin to add between boxes
            
        Returns:
            True if there's an overlap, False otherwise
        """
        for placed_box in self.placed_nodes:
            # Calculate bounds with margin
            box_left = box['x'] - box['width']/2 - margin
            box_right = box['x'] + box['width']/2 + margin
            box_top = box['y'] + box['height']/2 + margin
            box_bottom = box['y'] - box['height']/2 - margin
            
            placed_left = placed_box['x'] - placed_box['width']/2 - margin
            placed_right = placed_box['x'] + placed_box['width']/2 + margin
            placed_top = placed_box['y'] + placed_box['height']/2 + margin
            placed_bottom = placed_box['y'] - placed_box['height']/2 - margin
            
            # Check for overlap using AABB (Axis-Aligned Bounding Box) collision
            if not (box_right < placed_left or 
                    box_left > placed_right or
                    box_top < placed_bottom or
                    box_bottom > placed_top):
                return True
        
        return False
    
    def _draw_central_node(self, text: str) -> None:
        """Draw the central topic node."""
        wrapped_text = self._wrap_text(text, 20)
        
        # Draw the box
        box = FancyBboxPatch(
            (-1.5, -0.5), 3, 1,
            boxstyle="round,pad=0.1",
            facecolor=self.colors['central'],
            edgecolor=self.colors['text'],
            linewidth=2,
            zorder=10
        )
        self.ax.add_patch(box)
        
        # Draw the text
        self.ax.text(
            0, 0, wrapped_text,
            ha='center', va='center',
            fontsize=14, fontweight='bold',
            color='white',
            zorder=11
        )
    
    def _draw_idea_node(self, idea: Dict, x: float, y: float, angle: float) -> None:
        """Draw an idea node with its details."""
        title = idea.get('title', 'Untitled Idea')
        description = idea.get('description', '')
        
        # Truncate description to max 100 characters
        if len(description) > 100:
            description = description[:97] + '...'
        
        # Wrap text
        wrapped_title = self._wrap_text(title, 15)
        wrapped_desc = self._wrap_text(description, 30)
        
        # Calculate box size based on content
        box_width, box_height = self._calculate_box_dimensions(idea)
        
        # Draw main idea box
        box = FancyBboxPatch(
            (x - box_width/2, y - box_height/2), box_width, box_height,
            boxstyle="round,pad=0.08",
            facecolor=self.colors['main_idea'],
            edgecolor=self.colors['text'],
            linewidth=1.5,
            zorder=5
        )
        self.ax.add_patch(box)
        
        # Draw title
        self.ax.text(
            x, y + box_height/3, wrapped_title,
            ha='center', va='center',
            fontsize=10, fontweight='bold',
            color=self.colors['text'],
            zorder=6
        )
        
        # Draw description
        if description:
            self.ax.text(
                x, y - box_height/6, wrapped_desc,
                ha='center', va='center',
                fontsize=7,
                color=self.colors['text'],
                zorder=6
            )
    
    def _draw_connection(self, start: tuple, end: tuple, style: str = 'main') -> None:
        """Draw a connection line between nodes."""
        if style == 'main':
            linewidth = 2
            alpha = 0.6
        else:  # detail
            linewidth = 1
            alpha = 0.4
        
        arrow = FancyArrowPatch(
            start, end,
            arrowstyle='-',
            linewidth=linewidth,
            color=self.colors['text'],
            alpha=alpha,
            zorder=1
        )
        self.ax.add_patch(arrow)
    
    def _wrap_text(self, text: str, width: int) -> str:
        """Wrap text to specified width."""
        return '\n'.join(textwrap.wrap(text, width=width))
    
    def save(self, output_path: str, dpi: int = 300) -> None:
        """
        Save the mindmap to a file.
        
        Args:
            output_path: Path where to save the image
            dpi: Resolution for the output image
        """
        if self.fig is None:
            raise ValueError("No mindmap has been created yet")
        
        self.fig.tight_layout()
        self.fig.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                        facecolor=self.colors['background'])
        print(f"Mindmap saved to: {output_path}")
    
    def show(self) -> None:
        """Display the mindmap."""
        if self.fig is None:
            raise ValueError("No mindmap has been created yet")
        
        plt.tight_layout()
        plt.show()


def create_mindmap_from_file(input_file: str, output_file: str = None, 
                             title: str = "Brainstorming Results") -> None:
    """
    Create a mindmap from a JSON file containing brainstorming results.
    
    Args:
        input_file: Path to JSON file with brainstorming results
        output_file: Path for output image (optional, will auto-generate if not provided)
        title: Title for the mindmap
    """
    # Read input file
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        data = json.load(f)
    
    # Create mindmap
    mindmap = BrainstormingMindmap(title=title)
    mindmap.create_from_extraction(data)
    
    # Generate output filename if not provided
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_mindmap.png")
    
    # Save and display
    mindmap.save(output_file)
    mindmap.show()


if __name__ == "__main__":
    file_load = False
    results = None

    if file_load:
        # Load results from file (for demonstration)
        with open('brainstorming_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    else:
        from tinytroupe.agent import TinyPerson
        from tinytroupe.environment import TinyWorld
        from tinytroupe.extraction import ResultsExtractor

        # Load agents
        lisa = TinyPerson.load_specification("./examples/agents/Lisa.agent.json")
        oscar = TinyPerson.load_specification("./examples/agents/Oscar.agent.json")

        # Run brainstorming session
        world = TinyWorld("Brainstorming", [lisa, oscar])
        world.broadcast("Let's brainstorm AI features for productivity tools. Keep concise and less than 100 words each.")
        world.run(1)

        # Extract results
        rapporteur = world.get_agent_by_name("Lisa Carter")
        extractor = ResultsExtractor()
        results = extractor.extract_results_from_agent(
            rapporteur,
            extraction_objective="Extract ideas with title, description, and details",
            situation="Brainstorming session"
        )

        # Save results to file
        with open('brainstorming_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

    if results:
        # Create mindmap
        mindmap = BrainstormingMindmap(title="AI Features Brainstorming")
        mindmap.create_from_extraction(results)
        mindmap.save('brainstorming_mindmap.png')
        mindmap.show()


