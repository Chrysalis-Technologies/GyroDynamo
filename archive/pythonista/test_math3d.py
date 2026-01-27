import math
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from mobile.pythonista.armillary_sphere import (
    quat_from_axis_angle,
    quat_rotate,
    norm,
    look_at,
    perspective,
    project_point,
)


def test_quat_rotation_preserves_length():
    v = (1.0, 2.0, -3.0)
    q = quat_from_axis_angle((0, 1, 0), 1.234)
    v2 = quat_rotate(q, v)
    assert abs(norm(v2) - norm(v)) < 1e-6


def test_perspective_depth_order():
    eye = (0, 0, 0)
    target = (0, 0, -1)
    up = (0, 1, 0)
    view = look_at(eye, target, up)
    proj = perspective(60, 1.0, 0.1, 100.0)
    near_pt = (0, 0, -2)
    far_pt = (0, 0, -5)
    _, _, zn = project_point(near_pt, view, proj, 200, 200)
    _, _, zf = project_point(far_pt, view, proj, 200, 200)
    assert zn < zf


def test_projection_center():
    view = look_at((0, 0, 0), (0, 0, -1), (0, 1, 0))
    proj = perspective(60, 2.0, 0.1, 100.0)
    sx, sy, _ = project_point((0, 0, -10), view, proj, 200, 100)
    assert abs(sx - 100) < 1e-6
    assert abs(sy - 50) < 1e-6


if __name__ == '__main__':
    test_quat_rotation_preserves_length()
    test_perspective_depth_order()
    test_projection_center()
    print('ok')
