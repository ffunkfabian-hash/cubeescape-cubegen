"""Generation-3 everyday geometry and collision regressions from player screenshots."""
import unittest
from cubegen.models import generate_asset, REGISTRY
from cubegen.params import Style
from cubegen.families import collision_boxes
from cubegen.quality import check

class StandardGeometryTests(unittest.TestCase):
    def test_open_lockers_have_empty_compartments_and_shelves(self):
        for count in (1, 2, 4):
            for seed in (0, 7, 19):
                a = generate_asset('locker', seed, params=dict(count=count, height=2, open=True, bench=False), style=Style(wear='none'))
                shapes = collision_boxes(a, 'locker')
                # The open door is the large primitive angled away from the front.
                mesh = a.get('Body').mesh
                shelves = [p for p in mesh.parts if .018 < max(v[2] for v in mesh.verts[p.v0:p.v1])-min(v[2] for v in mesh.verts[p.v0:p.v1]) < .03
                           and max(v[1] for v in mesh.verts[p.v0:p.v1])-min(v[1] for v in mesh.verts[p.v0:p.v1]) > .2]
                self.assertGreaterEqual(len(shelves), 2)
                verts = mesh.verts[shelves[0].v0:shelves[0].v1]
                x = sum(v[0] for v in verts)/len(verts)
                self.assertFalse(any(s.contains((x, 0, 1)) for s in shapes))
                centre=tuple(sum(v[i] for v in verts)/len(verts) for i in range(3))
                self.assertTrue(any(s.contains(centre) for s in shapes))

    def test_bunk_ladder_enters_through_a_gap_with_a_rear_guard(self):
        for length in (1.6, 2, 2.4):
            for seed in (0, 7, 19):
                a = generate_asset('bed', seed, params=dict(style='bunk',length=length,blanket=False,lamp=False))
                gap = a.meta['ladder_entry']; shapes = collision_boxes(a, 'bed')
                self.assertFalse(any(s.contains(gap) for s in shapes))
                self.assertTrue(any(s.contains((0, -gap[1], gap[2])) for s in shapes))

    def test_large_floor_hatches_are_centred_and_framed(self):
        for size in ('1.0','2.0','4.0'):
            a = generate_asset('floor_tile', 19, params=dict(style='hatch',size=size,glow=False,stripes=False))
            self.assertEqual(a.meta['hatch_center'], [0,0])
            self.assertGreaterEqual(len(a.get('Deck').mesh.parts), 6)
            self.assertTrue(any(s.contains((0,0,-.02)) for s in collision_boxes(a,'floor_tile')))

    def test_all_railed_junctions_stay_within_budget_and_keep_connectors_open(self):
        from cubegen.models.kit import CATWALK_ARMS
        for shape in ('corner','tee','cross','landing','end'):
            for width in ('1.0','2.0'):
                a = generate_asset('catwalk', 19, params=dict(shape=shape,width=width,length='4.0',rails='both',supports=0,glow=False))
                q=check(a,REGISTRY['catwalk'].category,'top')
                self.assertEqual(q['errors'], [], (shape,width,q))
                self.assertIsNotNone(a.get('Rail'))
                for dx,dy in CATWALK_ARMS.get(shape,((-1,0),(1,0))):
                    self.assertFalse(any(s.contains((dx*1.96,dy*1.96,.5)) for s in collision_boxes(a,'catwalk')))

    def test_changed_types_have_coverage_in_all_damage_states(self):
        for type_,params in [('locker',dict(open=True)),('bed',dict(style='bunk')),('floor_tile',dict(style='hatch',size='4.0')),('catwalk',dict(shape='cross',rails='both',supports=0))]:
            for damage in ('intact','damaged','destroyed','fractured'):
                a=generate_asset(type_,19,params=params,style=Style(damage=damage,wear='none'))
                q=check(a,REGISTRY[type_].category,REGISTRY[type_].pivot)
                self.assertEqual(q['uncovered'],[],(type_,damage,q))

if __name__ == '__main__': unittest.main()
