"""Fallback geometry generator — last-resort module emission for failed tasks.

Активируется ТОЛЬКО когда orchestrator маркирует task как failed (все retries+repair исчерпаны).
Возвращает простой valid JS module чтобы prompt НЕ был skipped в submission.

Стратегия:
- Lookup motif_hint OR object_type → matching template
- Fallback по умолчанию: серый сферический объект (recognizable, valid, минимальный)
- Все templates прошли validator + render-service (sanity verified during dev)

Реализация чисто аддитивная — НЕ trogает success path. Вызывается только из orchestrator._on_terminal.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# === Per-class fallback templates ===
# Keys: motif_hint OR object_type values (lowercase). All emit valid validator-compliant JS.
# Smaller/simpler than user submission — but valid, recognizable, ≤50KB literal.

_FALLBACK_TEMPLATES: dict[str, str] = {
    "chair": """\
export default function generate(THREE) {
  const woodMat = new THREE.MeshStandardMaterial({color: 0x8b6f47, metalness: 0.0, roughness: 0.7});
  const root = new THREE.Group();
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.04, 0.45), woodMat);
  seat.position.y = 0.40;
  root.add(seat);
  const legGeom = new THREE.CylinderGeometry(0.022, 0.022, 0.40, 16);
  for (const [x, z] of [[0.20, 0.20], [-0.20, 0.20], [0.20, -0.20], [-0.20, -0.20]]) {
    const leg = new THREE.Mesh(legGeom, woodMat);
    leg.position.set(x, 0.20, z);
    root.add(leg);
  }
  const backrest = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.45, 0.025), woodMat);
  backrest.position.set(0, 0.65, -0.21);
  root.add(backrest);
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "table": """\
export default function generate(THREE) {
  const mat = new THREE.MeshStandardMaterial({color: 0x8b6f47, metalness: 0.0, roughness: 0.6});
  const root = new THREE.Group();
  const top = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.04, 0.45), mat);
  top.position.y = 0.40;
  root.add(top);
  const legGeom = new THREE.CylinderGeometry(0.022, 0.022, 0.40, 16);
  for (const [x, z] of [[0.32, 0.20], [-0.32, 0.20], [0.32, -0.20], [-0.32, -0.20]]) {
    const leg = new THREE.Mesh(legGeom, mat);
    leg.position.set(x, 0.20, z);
    root.add(leg);
  }
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "bottle": """\
export default function generate(THREE) {
  const glass = new THREE.MeshPhysicalMaterial({color: 0xddeedd, metalness: 0.0, roughness: 0.05, transmission: 0.95, ior: 1.5, transparent: true});
  const profile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.18, 0.00),
    new THREE.Vector2(0.18, 0.45),
    new THREE.Vector2(0.10, 0.55),
    new THREE.Vector2(0.05, 0.60),
    new THREE.Vector2(0.05, 0.85),
    new THREE.Vector2(0.06, 0.90),
    new THREE.Vector2(0.00, 0.92),
  ];
  const root = new THREE.Group();
  root.add(new THREE.Mesh(new THREE.LatheGeometry(profile, 32), glass));
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "mug": """\
export default function generate(THREE) {
  const mat = new THREE.MeshStandardMaterial({color: 0xeeeeee, metalness: 0.0, roughness: 0.4});
  const profile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.20, 0.00),
    new THREE.Vector2(0.20, 0.50),
    new THREE.Vector2(0.18, 0.50),
    new THREE.Vector2(0.18, 0.05),
    new THREE.Vector2(0.00, 0.05),
  ];
  const root = new THREE.Group();
  root.add(new THREE.Mesh(new THREE.LatheGeometry(profile, 32), mat));
  // handle
  const handlePath = [
    new THREE.Vector3(0.20, 0.10, 0),
    new THREE.Vector3(0.32, 0.15, 0),
    new THREE.Vector3(0.32, 0.40, 0),
    new THREE.Vector3(0.20, 0.45, 0),
  ];
  const curve = new THREE.CatmullRomCurve3(handlePath);
  const handle = new THREE.Mesh(new THREE.TubeGeometry(curve, 16, 0.025, 8, false), mat);
  root.add(handle);
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "vase": """\
export default function generate(THREE) {
  const mat = new THREE.MeshStandardMaterial({color: 0xa84432, metalness: 0.0, roughness: 0.4});
  const profile = [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.25, 0.00),
    new THREE.Vector2(0.30, 0.20),
    new THREE.Vector2(0.20, 0.55),
    new THREE.Vector2(0.25, 0.85),
    new THREE.Vector2(0.22, 1.00),
    new THREE.Vector2(0.00, 1.00),
  ];
  const root = new THREE.Group();
  root.add(new THREE.Mesh(new THREE.LatheGeometry(profile, 32), mat));
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "lamp": """\
export default function generate(THREE) {
  const baseMat = new THREE.MeshStandardMaterial({color: 0x888888, metalness: 0.7, roughness: 0.3});
  const shadeMat = new THREE.MeshStandardMaterial({color: 0xffe699, metalness: 0.0, roughness: 0.6, emissive: 0xffe699, emissiveIntensity: 0.3});
  const root = new THREE.Group();
  // base
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.05, 32), baseMat);
  base.position.y = 0.025;
  root.add(base);
  // pole
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.55, 16), baseMat);
  pole.position.y = 0.33;
  root.add(pole);
  // shade
  const shade = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.25, 0.18, 32), shadeMat);
  shade.position.y = 0.70;
  root.add(shade);
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "car": """\
export default function generate(THREE) {
  const bodyMat = new THREE.MeshStandardMaterial({color: 0xa11919, metalness: 0.6, roughness: 0.4});
  const tireMat = new THREE.MeshStandardMaterial({color: 0x222222, metalness: 0.0, roughness: 0.9});
  const root = new THREE.Group();
  // body
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.18, 0.32), bodyMat);
  body.position.y = 0.16;
  root.add(body);
  // cabin
  const cabin = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.14, 0.30), bodyMat);
  cabin.position.set(0.0, 0.32, 0.0);
  root.add(cabin);
  // wheels
  const wheelGeom = new THREE.CylinderGeometry(0.08, 0.08, 0.04, 24);
  for (const [x, z] of [[0.22, 0.16], [-0.22, 0.16], [0.22, -0.16], [-0.22, -0.16]]) {
    const w = new THREE.Mesh(wheelGeom, tireMat);
    w.rotation.z = Math.PI / 2;
    w.position.set(x, 0.08, z);
    root.add(w);
  }
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",

    "knife": """\
export default function generate(THREE) {
  const bladeMat = new THREE.MeshStandardMaterial({color: 0xcccccc, metalness: 0.9, roughness: 0.2});
  const handleMat = new THREE.MeshStandardMaterial({color: 0x3c2415, metalness: 0.0, roughness: 0.7});
  const root = new THREE.Group();
  // blade — extruded silhouette with bevel
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.lineTo(0.04, 0.0);
  shape.lineTo(0.04, 0.45);
  shape.lineTo(0.00, 0.50);
  shape.lineTo(0, 0);
  const bladeGeom = new THREE.ExtrudeGeometry(shape, {depth: 0.025, bevelEnabled: true, bevelThickness: 0.020, bevelSize: 0.010, bevelSegments: 4});
  const blade = new THREE.Mesh(bladeGeom, bladeMat);
  blade.position.set(0.0, 0.10, 0);
  blade.rotation.z = Math.PI / 2;
  root.add(blade);
  // handle
  const handle = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.04, 0.04), handleMat);
  handle.position.set(-0.30, 0.10, 0);
  root.add(handle);
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
""",
    # === lathemix-added motifs (Phase 5 expansion) ===
    "phone": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.62, 0.04), new THREE.MeshStandardMaterial({color: 0x1a1a1a, metalness: 0.2, roughness: 0.4}));
  root.add(body);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.26, 0.52), new THREE.MeshStandardMaterial({color: 0x0a0a14, emissive: 0x222244, emissiveIntensity: 0.4}));
  screen.position.z = 0.021;
  root.add(screen);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "tree": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({color: 0x6b4226, roughness: 0.9});
  const leafMat = new THREE.MeshStandardMaterial({color: 0x3d7a3a, roughness: 0.8});
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.55, 16), trunkMat);
  trunk.position.y = 0.05; root.add(trunk);
  // canopy: 30 leaf planes via golden-angle scatter
  for (let i = 0; i < 30; i++) {
    const angle = i * 2.399;
    const r = 0.20 + 0.04 * Math.sin(i * 1.3);
    const y = 0.38 + 0.15 * Math.cos(i * 0.9);
    const leaf = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.08), leafMat);
    leaf.position.set(Math.cos(angle)*r, y, Math.sin(angle)*r);
    leaf.rotation.set(angle*0.3, angle, 0);
    root.add(leaf);
  }
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "flower": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const stemMat = new THREE.MeshStandardMaterial({color: 0x3d7a3a, roughness: 0.7});
  const petalMat = new THREE.MeshStandardMaterial({color: 0xd84a6c, roughness: 0.6});
  const centerMat = new THREE.MeshStandardMaterial({color: 0xf5d04a, roughness: 0.5});
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.015, 0.55, 12), stemMat);
  stem.position.y = -0.05; root.add(stem);
  const center = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), centerMat);
  center.position.y = 0.25; root.add(center);
  // 8 petals
  for (let i = 0; i < 8; i++) {
    const angle = i * Math.PI * 2 / 8;
    const petal = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 8), petalMat);
    petal.scale.set(1, 0.3, 0.5);
    petal.position.set(Math.cos(angle)*0.09, 0.25, Math.sin(angle)*0.09);
    petal.rotation.y = angle; root.add(petal);
  }
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "potted_plant": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const potMat = new THREE.MeshStandardMaterial({color: 0xb46a3f, roughness: 0.85});
  const leafMat = new THREE.MeshStandardMaterial({color: 0x4a8c44, roughness: 0.8});
  // pot via lathe
  const profile = [];
  for (let i = 0; i <= 8; i++) { const t = i/8; profile.push(new THREE.Vector2(0.14 + 0.04*Math.sin(t*Math.PI), -0.2 + t*0.18)); }
  const pot = new THREE.Mesh(new THREE.LatheGeometry(profile, 24), potMat);
  root.add(pot);
  // 15 leaf scatter
  for (let i = 0; i < 15; i++) {
    const angle = i * 2.399;
    const r = 0.05 + 0.05 * Math.sin(i * 1.1);
    const y = 0.05 + 0.30 * (i / 15);
    const leaf = new THREE.Mesh(new THREE.PlaneGeometry(0.10, 0.05), leafMat);
    leaf.position.set(Math.cos(angle)*r, y, Math.sin(angle)*r);
    leaf.rotation.set(0.3, angle, 0.2); root.add(leaf);
  }
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "hammer": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.03, 0.5, 16), new THREE.MeshStandardMaterial({color: 0x6b4226, roughness: 0.85}));
  handle.position.y = -0.05; root.add(handle);
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.08, 0.06), new THREE.MeshStandardMaterial({color: 0x4a4a4a, metalness: 0.85, roughness: 0.3}));
  head.position.y = 0.24; root.add(head);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "scissors": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const bladeMat = new THREE.MeshStandardMaterial({color: 0xc0c0c0, metalness: 0.9, roughness: 0.2});
  const handleMat = new THREE.MeshStandardMaterial({color: 0xd84a4a, roughness: 0.5});
  for (let s = -1; s <= 1; s += 2) {
    const shape = new THREE.Shape();
    shape.moveTo(0, 0); shape.lineTo(0.05, 0.20); shape.lineTo(0.0, 0.32); shape.lineTo(-0.02, 0.08); shape.lineTo(0, 0);
    const blade = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, {depth: 0.005, bevelEnabled: false}), bladeMat);
    blade.scale.x = s; root.add(blade);
    const loop = new THREE.Mesh(new THREE.TorusGeometry(0.06, 0.012, 8, 24), handleMat);
    loop.position.set(s * 0.08, -0.10, 0); loop.rotation.x = Math.PI/2; root.add(loop);
  }
  const pivot = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.02, 16), new THREE.MeshStandardMaterial({color: 0x808080, metalness: 0.8}));
  pivot.rotation.x = Math.PI/2; root.add(pivot);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "laptop": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const baseMat = new THREE.MeshStandardMaterial({color: 0x2a2a2a, metalness: 0.3, roughness: 0.5});
  const screenMat = new THREE.MeshStandardMaterial({color: 0x0a0a14, emissive: 0x222244, emissiveIntensity: 0.5});
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.02, 0.4), baseMat);
  root.add(base);
  const lid = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.40, 0.02), baseMat);
  lid.position.set(0, 0.20, -0.20); lid.rotation.x = -0.15; root.add(lid);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.34), screenMat);
  screen.position.set(0, 0.20, -0.19); screen.rotation.x = -0.15; root.add(screen);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "headphones": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({color: 0x1a1a1a, metalness: 0.4, roughness: 0.5});
  for (let s = -1; s <= 1; s += 2) {
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.10, 32), mat);
    cup.position.set(s * 0.20, 0, 0); cup.rotation.z = Math.PI/2; root.add(cup);
  }
  // headband: curved tube
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.20, 0.05, 0),
    new THREE.Vector3(0, 0.22, 0),
    new THREE.Vector3(0.20, 0.05, 0),
  ]);
  const band = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.018, 12, false), mat);
  root.add(band);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "camera": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const bodyMat = new THREE.MeshStandardMaterial({color: 0x1a1a1a, metalness: 0.3, roughness: 0.5});
  const lensMat = new THREE.MeshStandardMaterial({color: 0x0a0a0a, metalness: 0.7, roughness: 0.2});
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.30, 0.15), bodyMat);
  root.add(body);
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.11, 0.18, 32), lensMat);
  lens.position.z = 0.16; lens.rotation.x = Math.PI/2; root.add(lens);
  const viewfinder = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.06, 0.10), bodyMat);
  viewfinder.position.y = 0.18; root.add(viewfinder);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "box": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({color: 0xb46a3f, roughness: 0.85});
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.6, 0.35), mat);
  root.add(body);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "can": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const bodyMat = new THREE.MeshStandardMaterial({color: 0xc83a3a, metalness: 0.4, roughness: 0.4});
  const rimMat = new THREE.MeshStandardMaterial({color: 0xc0c0c0, metalness: 0.9, roughness: 0.2});
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 0.55, 32), bodyMat);
  root.add(body);
  const topRim = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.012, 8, 32), rimMat);
  topRim.position.y = 0.275; topRim.rotation.x = Math.PI/2; root.add(topRim);
  const botRim = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.012, 8, 32), rimMat);
  botRim.position.y = -0.275; botRim.rotation.x = Math.PI/2; root.add(botRim);
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
    "doll": """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const skinMat = new THREE.MeshStandardMaterial({color: 0xf0c8a8, roughness: 0.8});
  const clothMat = new THREE.MeshStandardMaterial({color: 0xd84a6c, roughness: 0.85});
  // proportions: head 1/4, torso 1/3, limbs 1/3
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.16, 24, 18), skinMat);
  head.position.y = 0.42; root.add(head);
  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.20, 0.30, 0.12), clothMat);
  torso.position.y = 0.10; root.add(torso);
  for (let s = -1; s <= 1; s += 2) {
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.04, 0.20, 8, 16), clothMat);
    arm.position.set(s*0.13, 0.10, 0); root.add(arm);
    const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.22, 8, 16), clothMat);
    leg.position.set(s*0.06, -0.20, 0); root.add(leg);
  }
  fitToUnitCube(THREE, root); return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(), center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const scale = 0.95 / (Math.max(size.x, size.y, size.z) || 1);
  root.scale.setScalar(scale);
  root.position.set(-center.x*scale, -center.y*scale, -center.z*scale);
}
""",
}

# Aliases — поведение для motif_hint вариантов
_ALIASES: dict[str, str] = {
    "stool": "chair",
    "armchair": "chair",
    "sofa": "chair",
    "couch": "chair",
    "desk": "table",
    "bench": "table",
    "lampshade": "lamp",
    "lantern": "lamp",
    "vehicle": "car",
    "truck": "car",
    "automobile": "car",
    "wineglass": "bottle",
    "goblet": "bottle",
    "flask": "bottle",
    "cup": "mug",
    "pot": "vase",
    "urn": "vase",
    "blade": "knife",
    "dagger": "knife",
    "sword": "knife",
    # lathemix Phase 5 additions
    "smartphone": "phone",
    "mobile": "phone",
    "iphone": "phone",
    "tablet": "phone",
    "palm": "tree",
    "oak": "tree",
    "pine": "tree",
    "bush": "tree",
    "rose": "flower",
    "tulip": "flower",
    "daisy": "flower",
    "plant": "potted_plant",
    "houseplant": "potted_plant",
    "succulent": "potted_plant",
    "mallet": "hammer",
    "claw_hammer": "hammer",
    "shears": "scissors",
    "snips": "scissors",
    "notebook": "laptop",
    "macbook": "laptop",
    "earbuds": "headphones",
    "headset": "headphones",
    "dslr": "camera",
    "polaroid": "camera",
    "carton": "box",
    "package": "box",
    "tin": "can",
    "soda_can": "can",
    "beer_can": "can",
    "figurine": "doll",
    "toy": "doll",
    "plush": "doll",
}


# === Default fallback (universal — для unknown motifs) ===
_DEFAULT_FALLBACK = """\
export default function generate(THREE) {
  const root = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({color: 0x888888, metalness: 0.0, roughness: 0.7});
  root.add(new THREE.Mesh(new THREE.SphereGeometry(0.40, 32, 16), mat));
  fitToUnitCube(THREE, root);
  return root;
}
function fitToUnitCube(THREE, root) {
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3(); const center = new THREE.Vector3();
  box.getSize(size); box.getCenter(center);
  const maxDim = Math.max(size.x, size.y, size.z) || 1;
  const scale = 0.95 / maxDim;
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
}
"""


def _normalize_motif(value: str | None) -> str | None:
    """Normalize motif/object_type lookup key (lowercase, alias resolution)."""
    if not value:
        return None
    key = value.strip().lower()
    return _ALIASES.get(key, key)


def fallback_for(*, motif_hint: str | None = None, object_type: str | None = None) -> tuple[str, str]:
    """Return (js_code, motif_used) for given hint OR object_type.

    Lookup order:
        1. motif_hint exact match (after lowercase + alias)
        2. object_type exact match (after lowercase + alias)
        3. _DEFAULT_FALLBACK (gray sphere)
    """
    for candidate in (motif_hint, object_type):
        normalized = _normalize_motif(candidate)
        if normalized and normalized in _FALLBACK_TEMPLATES:
            return _FALLBACK_TEMPLATES[normalized], normalized
    return _DEFAULT_FALLBACK, "default_sphere"


def fallback_from_osd(osd_json_str: str | None) -> tuple[str, str]:
    """Parse OSD JSON string and pick fallback. Tolerant — never raises."""
    if not osd_json_str:
        return _DEFAULT_FALLBACK, "default_sphere"
    try:
        osd = json.loads(osd_json_str)
        return fallback_for(
            motif_hint=osd.get("motif_hint"),
            object_type=osd.get("object_type"),
        )
    except (json.JSONDecodeError, AttributeError, TypeError) as e:
        logger.warning("[fallback] OSD parse failed (%s); using default", e)
        return _DEFAULT_FALLBACK, "default_sphere"


def available_motifs() -> list[str]:
    """List all explicit fallback motifs (excludes default + aliases)."""
    return sorted(_FALLBACK_TEMPLATES.keys())
