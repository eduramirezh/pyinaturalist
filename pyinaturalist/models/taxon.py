from typing import Dict, List

from attr import define, field, fields_dict

from pyinaturalist.constants import API_V1_BASE_URL, JsonResponse
from pyinaturalist.models import BaseModel, LazyProperty, Photo, add_lazy_attrs, kwarg
from pyinaturalist.request_params import RANKS
from pyinaturalist.v1 import get_taxa_by_id


@define(auto_attribs=False, field_transformer=add_lazy_attrs)
class Taxon(BaseModel):
    """A dataclass containing information about a taxon, matching the schema of
    `GET /taxa <https://api.inaturalist.org/v1/docs/#!/Taxa/get_taxa>`_.

    Can be constructed from either a full JSON record, a partial JSON record, or just an ID.
    Examples of partial records include nested ``ancestors``, ``children``, and results from
    :py:func:`get_taxa_autocomplete`.
    """

    atlas_id: int = kwarg
    complete_rank: str = kwarg
    complete_species_count: int = kwarg
    extinct: bool = kwarg
    iconic_taxon_id: int = kwarg
    iconic_taxon_name: str = kwarg
    id: int = kwarg
    is_active: bool = kwarg
    listed_taxa_count: int = kwarg
    name: str = kwarg
    observations_count: int = kwarg
    parent_id: int = kwarg
    rank: str = kwarg
    rank_level: int = kwarg
    taxon_changes_count: int = kwarg
    taxon_schemes_count: int = kwarg
    wikipedia_summary: str = kwarg
    wikipedia_url: str = kwarg
    preferred_common_name: str = field(default='')

    # Nested collections
    ancestor_ids: List[int] = field(factory=list)
    conservation_statuses: List[str] = field(factory=list)
    current_synonymous_taxon_ids: List[int] = field(factory=list)
    flag_counts: Dict = field(factory=dict)
    listed_taxa: List = field(factory=list)

    # Lazy-loaded nested model objects
    ancestors: property = LazyProperty(BaseModel.from_json_list)
    children: property = LazyProperty(BaseModel.from_json_list)
    default_photo: property = LazyProperty(Photo.from_json)
    taxon_photos: property = LazyProperty(Photo.from_json_list)

    @classmethod
    def from_sorted_json_list(cls, value: JsonResponse) -> List['Taxon']:
        """Sort Taxon objects by rank then by name"""
        taxa = cls.from_json_list(value)
        taxa.sort(key=_get_rank_name_idx)
        return taxa  # type: ignore

    @property
    def ancestry(self) -> str:
        tokens = [t.name for t in self.ancestors] if self.ancestors else self.ancestor_ids
        return ' | '.join([str(t) for t in tokens])

    @property
    def parent(self) -> 'Taxon':
        """Return immediate parent, if any"""
        return self.ancestors[-1] if self.ancestors else None

    @property
    def url(self) -> str:
        return f'{API_V1_BASE_URL}/taxa/{self.id}'

    @classmethod
    def from_id(cls, id: int) -> 'Taxon':
        """Lookup and create a new Taxon object by ID"""
        r = get_taxa_by_id(id)
        return cls.from_json(r['results'][0])  # type: ignore

    def load_full_record(self):
        """Update this Taxon with full taxon info, including ancestors + children"""
        t = Taxon.from_id(self.id)
        for key in fields_dict(self.__class__).keys():
            key = key.lstrip('_')  # Use getters/setters for LazyProperty instead of temp attrs
            setattr(self, key, getattr(t, key))


# Since these use Taxon classmethods, they must be added after Taxon is defined
Taxon.ancestors = LazyProperty(Taxon.from_json_list, 'ancestors')
Taxon.children = LazyProperty(Taxon.from_sorted_json_list, 'children')


def _get_rank_name_idx(taxon):
    return _get_rank_idx(taxon.rank), taxon.name


def _get_rank_idx(rank: str) -> int:
    return RANKS.index(rank) if rank in RANKS else 0