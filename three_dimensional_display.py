"""Hybrid Pygame display backend for the hardware-accelerated 3D workspace."""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import pygame

from three_dimensional_ca import Position3D, Volume3D
from three_dimensional_rendering import (
    ModernGLVoxelRenderer,
    OrbitCamera3D,
    PatternPreview3D,
    VoxelRenderSettings,
)

try:
    import moderngl
except ImportError:  # pragma: no cover - handled by the runtime error path
    moderngl = None  # type: ignore[assignment]


class ThreeDimensionalDisplayError(RuntimeError):
    """Raised when the OpenGL 3D display cannot be created safely."""


def framebuffer_rgb_array(
    payload: bytes,
    size: tuple[int, int],
) -> np.ndarray:
    """Convert bottom-up OpenGL RGB bytes to a top-down byte-owning copy."""

    width, height = size
    expected = width * height * 3
    if width < 1 or height < 1 or len(payload) != expected:
        raise ValueError("Framebuffer RGB payload does not match its dimensions.")
    bottom_up = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 3)
    return np.flipud(bottom_up).copy()


class HybridDisplayBackend:
    """Keep 1D/2D on Pygame surfaces and use OpenGL only for the 3D workspace.

    Pygame widgets continue drawing into ``surface`` while the 3D backend is
    active. The transparent UI surface is uploaded once per frame and blended
    over the hardware-rendered voxel scene.
    """

    def __init__(self, size: tuple[int, int], caption: str) -> None:
        self.caption = caption
        self.size = size
        self.mode = "software"
        self.surface = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.context: Any | None = None
        self.voxel_renderer: ModernGLVoxelRenderer | None = None
        self._overlay_program: Any | None = None
        self._overlay_buffer: Any | None = None
        self._overlay_vao: Any | None = None
        self._overlay_texture: Any | None = None
        self._capture_revision = -1
        pygame.display.set_caption(caption)

    @property
    def is_opengl(self) -> bool:
        return self.mode == "opengl"

    @property
    def supports_3d(self) -> bool:
        return moderngl is not None and os.environ.get("SDL_VIDEODRIVER") != "dummy"

    def activate_software(self, size: tuple[int, int] | None = None) -> pygame.Surface:
        """Restore the established resizable software surface."""
        requested_size = self.size if size is None else size
        if self.mode == "software" and requested_size == self.size:
            return self.surface
        if size is not None:
            self.size = size
        if self.is_opengl:
            self._release_opengl_resources()
        self.surface = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        pygame.display.set_caption(self.caption)
        self.mode = "software"
        return self.surface

    def activate_3d(self, size: tuple[int, int] | None = None) -> pygame.Surface:
        """Create a core OpenGL context and return its transparent UI surface."""
        if size is not None:
            self.size = size
        if self.is_opengl:
            return self.surface
        if not self.supports_3d:
            if os.environ.get("SDL_VIDEODRIVER") == "dummy":
                self.mode = "software_3d_fallback"
                return self.surface
            raise ThreeDimensionalDisplayError(
                "ModernGL is not installed; run 'python -m pip install -r requirements.txt'."
            )

        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(
                pygame.GL_CONTEXT_PROFILE_MASK,
                pygame.GL_CONTEXT_PROFILE_CORE,
            )
            pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
            pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
            pygame.display.set_mode(
                self.size,
                pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE,
            )
            self.context = moderngl.create_context(require=330)
            self.voxel_renderer = ModernGLVoxelRenderer(self.context)
            self._create_overlay_resources()
            self.surface = pygame.Surface(self.size, pygame.SRCALPHA, 32)
            self.mode = "opengl"
            pygame.display.set_caption(self.caption)
            return self.surface
        except Exception as exc:
            self._release_opengl_resources()
            self.mode = "software"
            self.surface = pygame.display.set_mode(self.size, pygame.RESIZABLE)
            pygame.display.set_caption(self.caption)
            raise ThreeDimensionalDisplayError(
                f"OpenGL 3.3 context could not be created: {exc}"
            ) from exc

    def resize(self, size: tuple[int, int], use_3d: bool) -> pygame.Surface:
        """Recreate the selected backend after a native window resize."""
        self.size = size
        if use_3d and self.is_opengl:
            self._release_opengl_resources()
            self.mode = "software"
            return self.activate_3d(size)
        if use_3d and self.mode == "software_3d_fallback":
            self.surface = pygame.display.set_mode(size, pygame.RESIZABLE)
            return self.surface
        return self.activate_software(size)

    def begin_3d_frame(self, background: tuple[int, int, int]) -> None:
        """Clear color/depth buffers and reset the transparent Pygame UI layer."""
        if not self.is_opengl or self.context is None:
            self.surface.fill(background)
            return
        self.context.viewport = (0, 0, *self.size)
        self.context.scissor = None
        self.context.clear(
            *(channel / 255.0 for channel in background),
            alpha=1.0,
            depth=1.0,
        )
        self.surface.fill((0, 0, 0, 0))

    def render_volume(
        self,
        volume: Volume3D,
        camera: OrbitCamera3D,
        viewport: pygame.Rect,
        *,
        revision: int,
        alive_color: tuple[int, int, int],
        accent_color: tuple[int, int, int],
        selected: Position3D | None,
        settings: VoxelRenderSettings,
        preview: PatternPreview3D | None = None,
    ) -> bool:
        """Render an instanced voxel volume when an OpenGL context is active."""
        if not self.is_opengl or self.voxel_renderer is None:
            return False
        self.voxel_renderer.render(
            volume,
            camera,
            (viewport.x, viewport.y, viewport.width, viewport.height),
            self.size[1],
            revision=revision,
            alive_color=alive_color,
            accent_color=accent_color,
            selected=selected,
            settings=settings,
            preview=preview,
        )
        return True

    def capture_volume(
        self,
        volume: Volume3D,
        camera: OrbitCamera3D,
        size: tuple[int, int],
        *,
        background: tuple[int, int, int],
        alive_color: tuple[int, int, int],
        accent_color: tuple[int, int, int],
        settings: VoxelRenderSettings,
    ) -> np.ndarray:
        """Render one camera-accurate volume into an offscreen RGB framebuffer.

        OpenGL contexts are thread-affine, so this capture runs on the Pygame
        event thread. The returned byte-owning array can safely be handed to a
        background PNG/GIF/MP4 encoder.
        """

        width, height = (int(size[0]), int(size[1]))
        if width < 1 or height < 1:
            raise ValueError("3D export viewport dimensions must be positive.")
        if (
            not self.is_opengl
            or self.context is None
            or self.voxel_renderer is None
        ):
            raise ThreeDimensionalDisplayError(
                "A hardware OpenGL 3.3 viewport is required for 3D viewport export."
            )

        color_texture = None
        depth_buffer = None
        framebuffer = None
        try:
            color_texture = self.context.texture((width, height), components=3)
            depth_buffer = self.context.depth_renderbuffer((width, height))
            framebuffer = self.context.framebuffer(
                color_attachments=(color_texture,),
                depth_attachment=depth_buffer,
            )
            framebuffer.use()
            self.context.viewport = (0, 0, width, height)
            self.context.scissor = None
            self.context.clear(
                *(channel / 255.0 for channel in background),
                alpha=1.0,
                depth=1.0,
            )
            self._capture_revision -= 1
            self.voxel_renderer.render(
                volume,
                camera,
                (0, 0, width, height),
                height,
                revision=self._capture_revision,
                alive_color=alive_color,
                accent_color=accent_color,
                selected=None,
                settings=settings,
            )
            return framebuffer_rgb_array(
                framebuffer.read(components=3, alignment=1),
                (width, height),
            )
        except ThreeDimensionalDisplayError:
            raise
        except Exception as exc:
            raise ThreeDimensionalDisplayError(
                f"3D viewport could not be captured: {exc}"
            ) from exc
        finally:
            try:
                self.context.screen.use()
                self.context.viewport = (0, 0, *self.size)
                self.context.scissor = None
            except Exception:
                pass
            for resource in (framebuffer, depth_buffer, color_texture):
                if resource is not None:
                    try:
                        resource.release()
                    except Exception:
                        pass

    def present(self) -> None:
        """Composite Pygame UI over OpenGL, or flip the software display."""
        if not self.is_opengl:
            pygame.display.flip()
            return
        if (
            self.context is None
            or self._overlay_texture is None
            or self._overlay_vao is None
        ):
            raise ThreeDimensionalDisplayError("3D overlay resources are unavailable.")
        rgba = pygame.image.tobytes(self.surface, "RGBA", True)
        self._overlay_texture.write(rgba)
        self.context.viewport = (0, 0, *self.size)
        self.context.scissor = None
        self.context.enable_only(moderngl.BLEND)
        self.context.blend_func = (
            moderngl.SRC_ALPHA,
            moderngl.ONE_MINUS_SRC_ALPHA,
        )
        self._overlay_texture.use(location=0)
        self._overlay_vao.render(mode=moderngl.TRIANGLES)
        pygame.display.flip()

    def close(self) -> None:
        self._release_opengl_resources()

    def _create_overlay_resources(self) -> None:
        assert self.context is not None
        self._overlay_program = self.context.program(
            vertex_shader="""
                #version 330
                in vec2 in_position;
                in vec2 in_uv;
                out vec2 v_uv;
                void main() {
                    v_uv = in_uv;
                    gl_Position = vec4(in_position, 0.0, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform sampler2D ui_texture;
                in vec2 v_uv;
                out vec4 frag_color;
                void main() { frag_color = texture(ui_texture, v_uv); }
            """,
        )
        vertices = np.asarray(
            (
                (-1.0, -1.0, 0.0, 0.0),
                (1.0, -1.0, 1.0, 0.0),
                (1.0, 1.0, 1.0, 1.0),
                (-1.0, -1.0, 0.0, 0.0),
                (1.0, 1.0, 1.0, 1.0),
                (-1.0, 1.0, 0.0, 1.0),
            ),
            dtype=np.float32,
        )
        self._overlay_buffer = self.context.buffer(vertices.tobytes())
        self._overlay_vao = self.context.vertex_array(
            self._overlay_program,
            ((self._overlay_buffer, "2f 2f", "in_position", "in_uv"),),
        )
        self._overlay_texture = self.context.texture(self.size, components=4)
        self._overlay_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self._overlay_program["ui_texture"].value = 0

    def _release_opengl_resources(self) -> None:
        resources = (
            self._overlay_vao,
            self._overlay_texture,
            self._overlay_buffer,
            self._overlay_program,
            self.voxel_renderer,
        )
        for resource in resources:
            if resource is not None:
                try:
                    resource.release()
                except Exception:
                    pass
        if self.context is not None:
            try:
                self.context.release()
            except Exception:
                pass
        self.context = None
        self.voxel_renderer = None
        self._overlay_program = None
        self._overlay_buffer = None
        self._overlay_vao = None
        self._overlay_texture = None
