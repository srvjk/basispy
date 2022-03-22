#version 330 core
out vec4 color;

uniform vec3 polygonColor;

void main()
{
    color = vec4(polygonColor, 1.0);
}