"""
GPU stress test — uses pygame + PyOpenGL to send real work to the 3D engine.
Falls back to CPU-only if pygame/OpenGL are not installed.

Install GPU mode deps:
    pip install pygame PyOpenGL

Usage:
    python stress.py
"""
import sys
import os
import math
import time
import subprocess


def try_gpu_pygame():
    """Render a fullscreen spinning geometry loop via pygame + OpenGL."""
    try:
        import pygame
        from pygame.locals import DOUBLEBUF, OPENGL, FULLSCREEN
        from OpenGL.GL import (
            glClear, glClearColor, glBegin, glEnd, glVertex3f, glColor3f,
            glRotatef, glLoadIdentity, glTranslatef,
            GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_TRIANGLES,
        )
        from OpenGL.GLU import gluPerspective
    except ImportError:
        return False

    pygame.init()
    # Windowed so user can still see gpu_monitor
    screen = pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("GPU Stress — close window to stop")

    glClearColor(0.1, 0.1, 0.2, 1.0)
    gluPerspective(45, 800 / 600, 0.1, 50.0)
    glTranslatef(0.0, 0.0, -5.0)

    angle = 0.0
    print("[stress] pygame+OpenGL GPU stress running. Close the window to stop.")
    print("[stress] Watch the '3D' bar in gpu_monitor rise.\n")

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                running = False

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -5.0)
        glRotatef(angle, 1, 1, 0)

        # Draw many triangles to create real GPU load
        glBegin(GL_TRIANGLES)
        for i in range(2000):
            r = (i % 7) / 7.0
            g = (i % 11) / 11.0
            b = (i % 13) / 13.0
            glColor3f(r, g, b)
            a = math.radians(i * 0.5 + angle)
            glVertex3f(math.cos(a) * 2, math.sin(a) * 2, 0)
            glVertex3f(math.cos(a + 0.1) * 2, math.sin(a + 0.1) * 2, 0)
            glVertex3f(0, 0, math.sin(a))
        glEnd()

        pygame.display.flip()
        angle += 2.0
        clock.tick(0)  # uncapped FPS = maximum GPU load

    pygame.quit()
    return True


def cpu_stress_only():
    """CPU-only fallback that also indirectly loads the iGPU memory bus."""
    import threading
    import psutil

    core_count = psutil.cpu_count(logical=True)
    print(f"[stress] No pygame/OpenGL found. Running CPU-only stress on {core_count} threads.")
    print("[stress] NOTE: This will NOT show GPU engine utilization.")
    print("[stress] Install pygame + PyOpenGL for a real GPU test:\n")
    print("    pip install pygame PyOpenGL\n")
    print("[stress] Press Ctrl+C to stop.\n")

    stop = threading.Event()

    def worker():
        i = 0
        while not stop.is_set():
            _ = math.sqrt(i) * math.sin(i) * math.cos(i)
            i += 1

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(core_count)]
    for t in threads:
        t.start()

    try:
        t0 = time.time()
        while True:
            elapsed = int(time.time() - t0)
            print(f"\r[stress] Running {elapsed}s", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[stress] Stopping...")
        stop.set()


if __name__ == "__main__":
    print("=" * 50)
    print("  gpu_monitor — GPU stress test")
    print("=" * 50)
    print("Keep gpu_monitor running in another terminal.\n")

    if not try_gpu_pygame():
        cpu_stress_only()
