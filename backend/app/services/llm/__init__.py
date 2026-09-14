"""Provider-neutral LLM/semantic-analysis abstraction.

Nothing outside this package (and `app.analysis.semantic`, which consumes
it) should import a concrete provider or an LLM SDK directly -- the domain
and API layers only ever depend on the `AnalysisProvider` protocol in
`app.services.llm.provider`.
"""
