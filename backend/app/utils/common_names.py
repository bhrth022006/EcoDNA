"""
Shared scientific-name -> common-name lookup.

Covers two overlapping species sets used across this project:
  - the 18 freshwater/wetland taxa the classifier (ml_model/) was trained on,
    which are the same 18 used in the frontend's SPECIES sample array
  - the marine taxa seeded by seed.py / used in sample_dataset_with_sites.csv

For anything outside this list (e.g. a real dataset you upload with novel
species), get_common_name() falls back to returning None so callers can
degrade gracefully rather than showing a wrong or invented name.
"""

COMMON_NAMES = {
    # Classifier / freshwater sample species
    "Cyprinus carpio": "Common carp",
    "Salmo trutta": "Brown trout",
    "Anguilla anguilla": "European eel",
    "Rana temporaria": "Common frog",
    "Bufo bufo": "Common toad",
    "Anas platyrhynchos": "Mallard",
    "Baetis rhodani": "Mayfly nymph",
    "Libellula depressa": "Broad-bodied chaser",
    "Procambarus clarkii": "Red swamp crayfish",
    "Hydropsyche pellucidula": "Caddisfly larva",
    "Unio pictorum": "Painter's mussel",
    "Viviparus viviparus": "River snail",
    "Corbicula fluminea": "Asian clam",
    "Tubifex tubifex": "Sludge worm",
    "Navicula cryptocephala": "Diatom",
    "Cymbella affinis": "Diatom",
    "Nostoc commune": "Cyanobacterium",
    "Microcystis aeruginosa": "Bloom-forming cyanobacterium",

    # Marine species used in seed.py / sample_dataset_with_sites.csv
    "Salmo salar": "Atlantic salmon",
    "Gadus morhua": "Atlantic cod",
    "Thunnus albacares": "Yellowfin tuna",
    "Homarus americanus": "American lobster",
    "Mytilus edulis": "Blue mussel",
    "Calanus finmarchicus": "Calanoid copepod",
    "Laminaria digitata": "Oarweed (kelp)",
    "Undescribed eukaryote sp.": "Unidentified / novel taxon",
}


def get_common_name(species_name: str) -> str | None:
    return COMMON_NAMES.get(species_name)
