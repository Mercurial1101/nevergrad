# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import inspect
from typing import Optional, Tuple
from scipy import stats
import numpy as np
from ..common.typetools import ArrayLike
from . import sequences
from . import base
from .base import registry

# # # # # classes of optimizers # # # # #


class OneShotOptimizer(base.Optimizer):
    # pylint: disable=abstract-method
    one_shot = True


# # # # # very basic baseline optimizers # # # # #


@registry.register
class Zero(OneShotOptimizer):
    """Always returns 0 (including for the recommendation)
    """

    def _internal_ask(self) -> Tuple[float, ...]:
        return tuple([0] * self.dimension)


@registry.register
class RandomSearch(OneShotOptimizer):
    """Provides random suggestions, and a recommendation
    based on the best returned fitness values.
    Use StupidRandom instead if you would rather the recommendation
    should not be based on past fitness values.
    """

    def _internal_ask(self) -> base.ArrayLike:
        return np.random.normal(0, 1, self.dimension)


@registry.register
class CauchyRandomSearch(OneShotOptimizer):
    """Provides random suggestions, and a recommendation
    based on the best returned fitness values.
    Uses Cauchy distribution.
    """

    def _internal_ask(self) -> base.ArrayLike:
        return np.random.standard_cauchy(self.dimension)


@registry.register
class StupidRandom(RandomSearch):
    """Provides random suggestions, and a random recommendation
    which is *not* based on past fitness values.
    Use RandomSearch instead if you would rather the recommendation
    be based on past fitness values.
    """

    def _internal_provide_recommendation(self) -> base.ArrayLike:
        return np.random.normal(0, 1, self.dimension)


# # # # # implementations # # # # #


class _DetermisticSearch(OneShotOptimizer):

    def __init__(self, dimension: int, budget: Optional[int] = None, num_workers: int = 1) -> None:
        super().__init__(dimension, budget=budget, num_workers=num_workers)
        self._sampler_instance: Optional[sequences.Sampler] = None
        self._sampler = "Halton"
        self._middle_point = False
        self._scrambled = False
        self._cauchy = False
        self._scale = 1.

    @property
    def sampler(self) -> sequences.Sampler:
        if self._sampler_instance is None:
            budget = None if self.budget is None else self.budget  # TODO: - self._middle_point
            samplers = {"Halton": sequences.HaltonSampler,
                        "Hammersley": sequences.HammersleySampler,
                        "LHS": sequences.LHSSampler,
                        }
            self._sampler_instance = samplers[self._sampler](self.dimension, budget, scrambling=self._scrambled)
        return self._sampler_instance

    def _internal_ask(self) -> ArrayLike:
        # pylint: disable=not-callable
        if self._middle_point and not self._num_ask:
            return np.zeros(self.dimension)
        return self._scale * (stats.cauchy.ppf if self._cauchy else stats.norm.ppf)(self.sampler())


class DeterministicSearch(base.OptimizerFamily):
    """Halton low-discrepancy search.

    This is a one-shot optimization method, hopefully better than random search
    by ensuring more uniformity.
    However, Halton is a low quality sampling method when the dimension is high;
    it is usually better to use Halton with scrambling.
    When the budget is known in advance, it is also better to replace Halton by Hammersley.
    Reference: Halton 1964: Algorithm 247: Radical-inverse quasi-random point sequence, ACM, p. 701.
    Adds scrambling to the Halton search; much better in high dimension and rarely worse
    than the original Halton search.

    Adds scrambling to the Halton search; much better in high dimension and rarely worse
    than the original Halton search.

    hammersley version of the halton search.
    basically the key difference with halton is adding one coordinate evenly spaced.
    the discrepancy is better; but we need the budget in advance.

    Scrambled Hammersley sequence.
    This combines Scrambled Halton and Hammersley.

    Latin Hypercube Sampling.
    Though partially incremental versions exist, this implementation needs the budget in advance.
    This can be great in terms of discrepancy when the budget is not very high - for high
    budget, low discrepancy sequences (e.g. scrambled Hammersley) have a better discrepancy.

    Adding a middle point in the larger scale scrambled Halton search.
    The additional point is the very first one.
    """

    one_shot = True

    # pylint: disable=unused-argument
    def __init__(self, *, sampler: str = "Halton", scrambled: bool = False, middle_point: bool = False,
                 cauchy: bool = False, scale: float = 1.) -> None:
        # keep all parameters and set initialize superclass for print
        self._parameters = {x: y for x, y in locals().items() if x not in {"__class__", "self"}}
        defaults = {x: y.default for x, y in inspect.signature(self.__class__.__init__).parameters.items()}
        super().__init__(**{x: y for x, y in self._parameters.items() if y != defaults[x]})  # only print non defaults

    def __call__(self, dimension: int, budget: Optional[int] = None, num_workers: int = 1) -> _DetermisticSearch:
        run = _DetermisticSearch(dimension=dimension, budget=budget, num_workers=num_workers)
        # ugly but effective :s
        for name, value in self._parameters.items():
            setattr(run, "_" + name, value)
        run.name = repr(self)
        return run


HaltonSearch = DeterministicSearch().with_name("HaltonSearch", register=True)
HaltonSearchPlusMiddlePoint = DeterministicSearch(middle_point=True).with_name("HaltonSearchPlusMiddlePoint", register=True)
LargeHaltonSearch = DeterministicSearch(scale=100.).with_name("LargeHaltonSearch", register=True)
LargeScrHaltonSearch = DeterministicSearch(scale=100., scrambled=True).with_name("LargeScrHaltonSearch", register=True)
LargeHaltonSearchPlusMiddlePoint = DeterministicSearch(
    scale=100., middle_point=True).with_name("LargeHaltonSearchPlusMiddlePoint", register=True)
SmallHaltonSearchPlusMiddlePoint = DeterministicSearch(
    scale=.01, middle_point=True).with_name("SmallHaltonSearchPlusMiddlePoint", register=True)
ScrHaltonSearch = DeterministicSearch(scrambled=True).with_name("ScrHaltonSearch", register=True)
ScrHaltonSearchPlusMiddlePoint = DeterministicSearch(middle_point=True, scrambled=True).with_name("ScrHaltonSearchPlusMiddlePoint",
                                                                                                  register=True)
LargeScrHaltonSearchPlusMiddlePoint = DeterministicSearch(
    scale=100., middle_point=True, scrambled=True).with_name("LargeScrHaltonSearchPlusMiddlePoint", register=True)
SmallScrHaltonSearchPlusMiddlePoint = DeterministicSearch(
    scale=.01, middle_point=True, scrambled=True).with_name("SmallScrHaltonSearchPlusMiddlePoint", register=True)
HammersleySearch = DeterministicSearch(sampler="Hammersley").with_name("HammersleySearch", register=True)
HammersleySearchPlusMiddlePoint = DeterministicSearch(sampler="Hammersley", middle_point=True).with_name("HammersleySearchPlusMiddlePoint",
                                                                                                         register=True)
LargeHammersleySearchPlusMiddlePoint = DeterministicSearch(
    scale=100., sampler="Hammersley", middle_point=True).with_name("LargeHammersleySearchPlusMiddlePoint", register=True)
SmallHammersleySearchPlusMiddlePoint = DeterministicSearch(
    scale=.01, sampler="Hammersley", middle_point=True).with_name("SmallHammersleySearchPlusMiddlePoint", register=True)
LargeScrHammersleySearchPlusMiddlePoint = DeterministicSearch(
    scrambled=True, scale=100., sampler="Hammersley", middle_point=True).with_name("LargeScrHammersleySearchPlusMiddlePoint", register=True)
SmallScrHammersleySearchPlusMiddlePoint = DeterministicSearch(
    scrambled=True, scale=.01, sampler="Hammersley", middle_point=True).with_name("SmallScrHammersleySearchPlusMiddlePoint", register=True)
ScrHammersleySearchPlusMiddlePoint = DeterministicSearch(scrambled=True, sampler="Hammersley",
                                                         middle_point=True).with_name("ScrHammersleySearchPlusMiddlePoint", register=True)
LargeHammersleySearch = DeterministicSearch(scale=100., sampler="Hammersley").with_name("LargeHammersleySearch", register=True)
LargeScrHammersleySearch = DeterministicSearch(scale=100., sampler="Hammersley", scrambled=True).with_name("LargeScrHammersleySearch",
                                                                                                           register=True)
ScrHammersleySearch = DeterministicSearch(sampler="Hammersley", scrambled=True).with_name("ScrHammersleySearch", register=True)
CauchyScrHammersleySearch = DeterministicSearch(cauchy=True, sampler="Hammersley", scrambled=True).with_name("CauchyScrHammersleySearch",
                                                                                                             register=True)
LHSSearch = DeterministicSearch(sampler="LHS").with_name("LHSSearch", register=True)
CauchyLHSSearch = DeterministicSearch(sampler="LHS", cauchy=True).with_name("CauchyLHSSearch", register=True)


@registry.register
class LargerScaleRandomSearchPlusMiddlePoint(OneShotOptimizer):

    def _internal_ask(self) -> ArrayLike:
        if not self._num_ask:
            return np.zeros(self.dimension)
        return 500. * np.random.normal(0, 1, self.dimension)


@registry.register
class RandomSearchPlusMiddlePoint(OneShotOptimizer):
    """Random search plus a middle point.

    The middle point is the very first one."""

    def _internal_ask(self) -> ArrayLike:
        if not self._num_ask:
            return np.zeros(self.dimension)
        return np.random.normal(0, 1, self.dimension)


@registry.register
class SmallScaleRandomSearchPlusMiddlePoint(OneShotOptimizer):

    def _internal_ask(self) -> ArrayLike:
        if not self._num_ask:
            return np.zeros(self.dimension)
        return 0.01 * np.random.normal(0, 1, self.dimension)


@registry.register
class RandomScaleRandomSearchPlusMiddlePoint(OneShotOptimizer):

    def _internal_ask(self) -> ArrayLike:
        if not self._num_ask:
            return np.zeros(self.dimension)
        return np.exp(np.random.normal(0., 1.) - 2.) * np.random.normal(0., 1. / np.sqrt(self.dimension), self.dimension)


@registry.register
class RandomScaleRandomSearch(OneShotOptimizer):

    def _internal_ask(self) -> ArrayLike:
        return np.exp(np.random.normal(0., 1.) - 2.) * np.random.normal(0., 1. / np.sqrt(self.dimension), self.dimension)


@registry.register
class RescaleScrHammersleySearch(OneShotOptimizer):
    """Rescaled version of scrambled Hammersley search.

    We need the budget in advance, and rescale each variable linearly for almost matching the bounds.
    """

    def __init__(self, dimension: int, budget: Optional[int] = None, num_workers: int = 1) -> None:
        super().__init__(dimension, budget=budget, num_workers=num_workers)
        assert self.budget is not None, "A budget must be provided"
        self.sampler = sequences.ScrHammersleySampler(self.dimension, budget=self.budget)
        self.rescaler = sequences.Rescaler(self.sampler)
        self.sampler.reinitialize()
        self.iterator = iter(self.sampler)

    def _internal_ask(self) -> ArrayLike:
        return stats.norm.ppf(self.rescaler.apply(next(self.iterator)))
