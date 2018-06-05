import collections
import ixmp
import itertools

import pandas as pd

from message_ix.utils import isscalar


class Scenario(ixmp.Scenario):

    def __init__(self, platform, model, scen, version=None, annotation=None, cache=False):
        """Initialize a new message_ix.Scenario (structured input data and solution)
        or get an existing scenario from the ixmp database instance
        Parameters
        ----------
        platform : ixmp.Platform
        model : string
            model name
        scen : string
            scenario name
        version : string or integer
            initialize a new scenario (if version == 'new'), or
            load a specific version from the database (if version is integer)
        annotation : string
            a short annotation/comment (when initializing a new scenario)
        cache : boolean
            keep all dataframes in memory after first query (default: False)
        """
        jobj = platform._jobj
        if version == 'new':
            scheme = 'MESSAGE'
            jscen = jobj.newScenario(model, scen, scheme, annotation)
        elif isinstance(version, int):
            jscen = jobj.getScenario(model, scen, version)
        else:
            jscen = jobj.getScenario(model, scen)

        super(Scenario, self).__init__(
            platform, model, scen, jscen, cache=cache)

    def add_spatial_sets(self, data):
        """Add sets related to spatial dimensions of the model

        Parameters
        ----------
        data : dict or other

        Examples
        --------
        data = {'country': 'Austria'}
        data = {'country': ['Austria', 'Germany']}
        data = {'country': {'Austria': {'state': ['Vienna', 'Lower Austria']}}}
        """
        nodes = []
        levels = []
        hierarchy = []

        def recurse(k, v, parent='World'):
            if isinstance(v, collections.Mapping):
                for _parent, _data in v.items():
                    for _k, _v in _data.items():
                        recurse(_k, _v, parent=_parent)

            level = k
            children = [v] if isscalar(v) else v
            for child in children:
                hierarchy.append([level, child, parent])
                nodes.append(child)
            levels.append(level)

        for k, v in data.items():
            recurse(k, v)

        self.add_set("node", nodes)
        self.add_set("lvl_spatial", levels)
        self.add_set("map_spatial_hierarchy", hierarchy)

    def _add_defaults(self):
        """Add any default model structure if not already present"""
        # first model year
        cyear = self.set('cat_year')
        if cyear.empty or 'firstmodelyear' not in cyear['type_year']:
            fyear = self.set('year')[0]
            self.add_set("cat_year", "firstmodelyear", fyear)

    def to_gdx(self, *args, **kwargs):
        """See ixmp.Scenario.to_gdx() for documentation"""
        self._add_defaults()
        super(Scenario, self).to_gdx(*args, **kwargs)

    def add_temporal_sets(self, data):
        """Add sets related to temporal dimensions of the model

        Parameters
        ----------
        data : dict or other

        Examples
        --------
        data = {'year': [2010, 2020]}
        data = {'year': [2010, 2020], 'firstmodelyear': 2020}
        """
        if 'year' not in data:
            raise ValueError('"year" must be in temporal sets')
        horizon = data['year']
        self.add_set("year", horizon)

        first = data['firstmodelyear'] if 'firstmodelyear' in data else horizon[0]
        self.add_set("cat_year", ["firstmodelyear", first])

    def vintage_and_active_years(self):
        """Return a 2-tuple of valid pairs of vintage years and active years for
        use with data input.
        """
        horizon = self.set('year')
        combinations = itertools.product(horizon, horizon)
        year_pairs = [(y_v, y_a) for y_v, y_a in combinations if y_v <= y_a]
        v_years, a_years = zip(*year_pairs)
        return v_years, a_years
