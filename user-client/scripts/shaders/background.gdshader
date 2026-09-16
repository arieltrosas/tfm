shader_type sky;

uniform vec4 top_color : source_color = vec4(0.1, 0.1, 0.15, 1.0);
uniform vec4 bottom_color : source_color = vec4(0.35, 0.35, 0.45, 1.0);

void sky() {
    float t = clamp(EYEDIR.y * 0.5 + 0.5, 0.0, 1.0);
    COLOR = mix(bottom_color.rgb, top_color.rgb, t);
}