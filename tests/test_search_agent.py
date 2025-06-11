import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import asyncio

from guardian.core.research.Modules.agent.search import Search_agent

@pytest.mark.asyncio
async def test_search_agent_run_basic(monkeypatch):
    # Mock the model
    mock_model = MagicMock()
    # The LLM returns a fake plan as a JSON string inside markdown code block
    fake_plan = '[{"tool":"url_search","keyword":"AI","search_engine":"google"}]'
    mock_model.completion.return_value = f"```json\n{fake_plan}\n```"

    # Mock the Crawl class methods
    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        mock_crawl.get_url_llm = AsyncMock(return_value=[{'url': 'https://example.com'}])
        mock_crawl.get_summary = AsyncMock(return_value=[
            {'url': 'https://example.com', 'title': 'Example', 'summary': 'A summary', 'brief_summary': 'Brief', 'keywords': ['AI']}
        ])
        
        agent = Search_agent(model=mock_model)
        # Fake previous data for run() (simulate empty or primed db)
        data = []
        # Simulate a user query
        result = await agent.run("What is AI?", data)
        
        # Assertions!
        assert isinstance(result, dict)
        assert result['agent'] == "planner"
        assert isinstance(result['data'], list)
        assert len(result['data']) >= 1
        assert result['data'][0]['title'] == "Example"

@pytest.mark.asyncio
async def test_search_agent_handles_empty_plan(monkeypatch):
    # LLM returns an empty todo list
    mock_model = MagicMock()
    mock_model.completion.return_value = "```json\n[]\n```"

    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        agent = Search_agent(model=mock_model)
        result = await agent.run("This will fail", [])
        # Should not crash, db remains empty
        assert result['agent'] == "planner"
        assert result['data'] == []


# Additional tests
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_search_agent_handles_malformed_plan():
    # LLM returns malformed output, not JSON
    mock_model = MagicMock()
    mock_model.completion.return_value = "Here is some nonsense"

    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        agent = Search_agent(model=mock_model)
        result = await agent.run("garbage input", [])
        # Should not crash, should return empty data
        assert result['agent'] == "planner"
        assert result['data'] == []

@pytest.mark.asyncio
async def test_search_agent_handles_crawl_exception():
    mock_model = MagicMock()
    fake_plan = '[{"tool":"url_search","keyword":"AI","search_engine":"google"}]'
    mock_model.completion.return_value = f"```json\n{fake_plan}\n```"

    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        mock_crawl.get_url_llm = AsyncMock(side_effect=Exception("Failed to crawl"))
        mock_crawl.get_summary = AsyncMock(return_value=[])

        agent = Search_agent(model=mock_model)
        result = await agent.run("What is AI?", [])
        # Should not crash, should return empty data
        assert result['agent'] == "planner"
        assert result['data'] == []

@pytest.mark.asyncio
async def test_search_agent_multiple_results():
    mock_model = MagicMock()
    fake_plan = '[{"tool":"url_search","keyword":"AI","search_engine":"google"}]'
    mock_model.completion.return_value = f"```json\n{fake_plan}\n```"

    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        mock_crawl.get_url_llm = AsyncMock(return_value=[
            {'url': 'https://example.com/1'},
            {'url': 'https://example.com/2'}
        ])
        mock_crawl.get_summary = AsyncMock(return_value=[
            {'url': 'https://example.com/1', 'title': 'One', 'summary': 'Summary1', 'brief_summary': 'Brief1', 'keywords': ['AI']},
            {'url': 'https://example.com/2', 'title': 'Two', 'summary': 'Summary2', 'brief_summary': 'Brief2', 'keywords': ['AI']}
        ])

        agent = Search_agent(model=mock_model)
        result = await agent.run("What is AI?", [])
        assert isinstance(result['data'], list)
        assert len(result['data']) == 2
        titles = [d['title'] for d in result['data']]
        assert "One" in titles
        assert "Two" in titles

@pytest.mark.asyncio
async def test_search_agent_db_population():
    mock_model = MagicMock()
    fake_plan = '[{"tool":"url_search","keyword":"AI","search_engine":"google"}]'
    mock_model.completion.return_value = f"```json\n{fake_plan}\n```"

    with patch("guardian.core.research.Modules.agent.search.Crawl") as MockCrawl:
        mock_crawl = MockCrawl.return_value
        mock_crawl.get_url_llm = AsyncMock(return_value=[
            {'url': 'https://example.com'}
        ])
        mock_crawl.get_summary = AsyncMock(return_value=[
            {'url': 'https://example.com', 'title': 'Example', 'summary': 'A summary', 'brief_summary': 'Brief', 'keywords': ['AI']}
        ])

        agent = Search_agent(model=mock_model)
        data = []
        result = await agent.run("What is AI?", data)
        # The agent's internal db should reflect the research results
        assert hasattr(agent, 'db')
        assert isinstance(agent.db, list)
        assert len(agent.db) == 1
        assert agent.db[0]['title'] == 'Example'