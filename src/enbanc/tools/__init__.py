"""The tools `enbanc` ships. There is one.

    from enbanc.tools import web_search

    Advocate(tools=[web_search(api_key=...)])

The second of the package's two importable namespaces, and the last
(`docs/design/packaging.md`, "Two namespaces and nothing else"). Tools live here rather than
on the top level because `import enbanc` may not pull a provider SDK onto the import path,
and `import tavily` is exactly that — `tests/unit/test_import_is_inert.py` is what keeps the
two apart.

`web_search` is the only tool `0.1.0` ships. Database query and local file search are the
next two, and the `reference` contract is what makes them additive: a tool returning
`Source` needs nothing new from the library, which is why your own tool and this one are
the same kind of object.
"""

from ._web_search import web_search

# Re-export is `from ._module import Name` plus membership here — the same idiom the
# top-level `__init__.py` follows, and the second of the two lists
# `docs/design/packaging.md` ("The export surface") fixes.
__all__ = ["web_search"]
