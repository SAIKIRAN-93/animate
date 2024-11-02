import requests
import json
import os
import time
from moviepy.editor import *
from dotenv import load_dotenv
from typing import Tuple, List

class StabilityAnimationGenerator:
    def __init__(self):
        """Initialize the Stability AI animation generator."""
        load_dotenv()
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.base_url = "https://api.stability.ai"
        self.output_dir = "generated_animations"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def check_api_status(self) -> bool:
        """Check if Stability AI API is operational."""
        try:
            response = requests.get("https://stabilityai.instatus.com/summary.json")
            status_data = response.json()
            
            # Check if API is UP and there are no major outages
            is_up = status_data["page"]["status"] == "UP"
            has_major_outage = any(
                incident["impact"] == "MAJOROUTAGE" 
                for incident in status_data.get("activeIncidents", [])
            )
            
            return is_up and not has_major_outage
        except Exception as e:
            print(f"Failed to check API status: {e}")
            return False
            
    def check_components_status(self) -> bool:
        """Check if API components are operational."""
        try:
            response = requests.get("https://stabilityai.instatus.com/v2/components.json")
            components = response.json()
            
            # Check if all components are operational
            return all(comp["status"] == "OPERATIONAL" for comp in components)
        except Exception as e:
            print(f"Failed to check components status: {e}")
            return False
    
    def generate_scene_image(
        self, 
        scene_description: str, 
        resolution: Tuple[int, int] = (1024, 1024)
    ) -> str:
        """Generate an image using Stability AI API."""
        if not self.check_api_status() or not self.check_components_status():
            raise Exception("Stability AI API is currently experiencing issues")
            
        engine_id = "stable-diffusion-xl-1024-v1-0"
        api_endpoint = f"{self.base_url}/v1/generation/{engine_id}/text-to-image"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        data = {
            "text_prompts": [
                {
                    "text": f"{scene_description}, animation style, high quality, detailed",
                    "weight": 1
                }
            ],
            "cfg_scale": 7,
            "width": resolution[0],
            "height": resolution[1],
            "samples": 1,
            "steps": 30,
            "style_preset": "animation"
        }
        
        try:
            response = requests.post(api_endpoint, headers=headers, json=data)
            response.raise_for_status()
            
            # Save the generated image
            image_data = response.json()["artifacts"][0]["base64"]
            image_path = os.path.join(self.output_dir, f"scene_{int(time.time())}.png")
            
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(image_data))
                
            return image_path
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Image generation failed: {str(e)}")
    
    def create_animation(
        self, 
        script: str, 
        output_filename: str, 
        resolution: Tuple[int, int] = (1024, 1024), 
        fps: int = 24
    ) -> str:
        """Create animation from script using Stability AI generated images."""
        scenes = self._parse_script(script)
        clips = []
        
        for scene in scenes:
            try:
                # Generate scene image
                scene_image_path = self.generate_scene_image(
                    scene["description"], 
                    resolution=resolution
                )
                
                # Create base clip from image
                scene_duration = max(len(scene["actions"]) * 3, 5)  # Minimum 5 seconds
                scene_clip = ImageClip(scene_image_path).set_duration(scene_duration)
                
                # Add text overlays for actions
                text_clips = []
                for i, action in enumerate(scene["actions"]):
                    text_clip = TextClip(
                        action,
                        fontsize=30,
                        color='white',
                        bg_color='rgba(0,0,0,0.5)',
                        size=(resolution[0] - 100, None)
                    ).set_position(('center', 'bottom'))
                    
                    text_clip = text_clip.set_start(i * 3).set_duration(3)
                    text_clips.append(text_clip)
                
                # Combine scene and text
                scene_with_text = CompositeVideoClip(
                    [scene_clip] + text_clips,
                    size=resolution
                )
                clips.append(scene_with_text)
                
            except Exception as e:
                print(f"Error processing scene: {str(e)}")
                continue
        
        if not clips:
            raise Exception("No scenes were successfully generated")
            
        # Combine all scenes
        final_video = concatenate_videoclips(clips)
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Write final video
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264'
        )
        
        # Cleanup
        for clip in clips:
            clip.close()
        final_video.close()
        
        return output_path
    
    def _parse_script(self, script: str) -> List[dict]:
        """Parse the animation script into scenes."""
        scenes = []
        current_scene = {"description": "", "characters": [], "actions": []}
        
        for line in script.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('SCENE:'):
                if current_scene["description"]:
                    scenes.append(current_scene)
                current_scene = {
                    "description": line[6:].strip(),
                    "characters": [],
                    "actions": []
                }
            elif line.startswith('CHARACTER:'):
                current_scene["characters"].append(line[10:].strip())
            elif not line.startswith(('#', '//')):
                current_scene["actions"].append(line)
                
        if current_scene["description"]:
            scenes.append(current_scene)
            
        return scenes

def main():
    # Example usage
    script = """
    SCENE: A magical forest at sunset with glowing fireflies
    CHARACTER: Young wizard with flowing robes
    CHARACTER: Magical crystal staff
    The wizard raises their staff toward the sky
    Magical energy swirls around the crystal
    The fireflies gather in a spiral pattern
    
    SCENE: Ancient stone circle under starlight
    CHARACTER: Wizard
    CHARACTER: Spirit guardians
    The wizard steps into the center of the circle
    Ethereal spirit guardians materialize around them
    Magic pulses through the stone circle
    """
    
    try:
        generator = StabilityAnimationGenerator()
        output_path = generator.create_animation(
            script,
            "magical_scene.mp4",
            resolution=(1024, 1024),
            fps=24
        )
        print(f"Animation generated successfully: {output_path}")
        
    except Exception as e:
        print(f"Animation generation failed: {str(e)}")

if __name__ == "__main__":
    main()
