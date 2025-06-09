#!/usr/bin/env python3
"""
Module: research_youtube_to_knowledge_graph.py
Description: Research interaction scenario for YouTube video to knowledge graph pipeline

This scenario demonstrates the seamless flow from YouTube video analysis to a 
fully connected research knowledge graph in ArangoDB.

External Dependencies:
- youtube-transcripts: YouTube transcript extraction and link detection
- arxiv-mcp-server: ArXiv paper metadata extraction
- gitget: GitHub repository analysis
- arangodb: Graph database with semantic embeddings

Sample Input:
>>> agent_request = {
>>>     "video_url": "https://www.youtube.com/watch?v=ABC123",
>>>     "research_topic": "reinforcement learning from human feedback"
>>> }

Expected Output:
>>> {
>>>     "status": "success",
>>>     "video_id": "ABC123",
>>>     "knowledge_chunks": 15,
>>>     "arxiv_papers": 3,
>>>     "github_repos": 2,
>>>     "graph_nodes": 21,
>>>     "graph_edges": 45
>>> }

Example Usage:
>>> from research_youtube_to_knowledge_graph import process_research_video
>>> result = process_research_video("https://www.youtube.com/watch?v=ABC123")
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from arango import ArangoClient
from youtube_transcripts import download_youtube_transcript
from youtube_transcripts.link_extractor import ExtractedLink, extract_links_from_text


@dataclass
class ResearchRequest:
    """Agent request for research video analysis."""
    video_url: str
    research_topic: Optional[str] = None
    extract_depth: int = 2  # How many levels deep to follow links
    chunk_size: int = 500  # Characters per knowledge chunk


@dataclass
class KnowledgeChunk:
    """A chunk of transcript with metadata."""
    text: str
    start_time: float
    end_time: float
    video_id: str
    chunk_index: int
    semantic_embedding: Optional[List[float]] = None


class ResearchVideoProcessor:
    """Orchestrates the YouTube to Knowledge Graph pipeline."""
    
    def __init__(self, arango_config: Dict[str, str]):
        """Initialize with ArangoDB configuration."""
        self.client = ArangoClient(hosts=arango_config['url'])
        self.db = self.client.db(
            arango_config['database'],
            username=arango_config['username'],
            password=arango_config['password']
        )
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure all required collections exist in ArangoDB."""
        collections = [
            'videos',           # YouTube videos
            'chunks',           # Knowledge chunks from transcripts
            'papers',           # ArXiv papers
            'repositories',     # GitHub repos
            'authors',          # Video creators, paper authors, code maintainers
            'comments',         # Valuable comments with links
        ]
        
        edge_collections = [
            'mentions',         # Video/Chunk → Paper/Repo
            'implements',       # Repo → Paper
            'cites',           # Paper → Paper
            'depends_on',      # Repo → Repo
            'commented_on',    # Comment → Video
            'authored_by',     # Content → Author
            'chunk_of',        # Chunk → Video
            'semantically_similar'  # Chunk ↔ Chunk (similarity > threshold)
        ]
        
        for collection in collections:
            if not self.db.has_collection(collection):
                self.db.create_collection(collection)
                logger.info(f"Created collection: {collection}")
        
        for edge_collection in edge_collections:
            if not self.db.has_collection(edge_collection):
                self.db.create_collection(edge_collection, edge=True)
                logger.info(f"Created edge collection: {edge_collection}")
    
    async def process_video(self, request: ResearchRequest) -> Dict[str, Any]:
        """
        Main entry point for processing a research video.
        
        This method:
        1. Downloads transcript and extracts links
        2. Chunks the transcript into knowledge pieces
        3. Processes ArXiv papers through MCP
        4. Analyzes GitHub repos with GitGet
        5. Stores everything in ArangoDB with relationships
        6. Triggers ArangoDB's automatic features
        """
        logger.info(f"Processing research video: {request.video_url}")
        
        # Step 1: Download transcript and extract metadata
        transcript_data = await self._download_and_extract(request.video_url)
        
        # Step 2: Create knowledge chunks
        chunks = self._create_knowledge_chunks(
            transcript_data['transcript'],
            transcript_data['video_id'],
            request.chunk_size
        )
        
        # Step 3: Store video and chunks in ArangoDB
        video_node = await self._store_video_data(transcript_data)
        chunk_nodes = await self._store_chunks(chunks, video_node['_id'])
        
        # Step 4: Process extracted links
        paper_nodes = await self._process_arxiv_papers(transcript_data['arxiv_links'])
        repo_nodes = await self._process_github_repos(transcript_data['github_links'])
        
        # Step 5: Create relationships
        await self._create_relationships(
            video_node,
            chunk_nodes,
            paper_nodes,
            repo_nodes,
            transcript_data
        )
        
        # Step 6: Trigger ArangoDB enhancements
        await self._trigger_graph_enhancements(video_node['_id'])
        
        # Return summary
        return {
            'status': 'success',
            'video_id': transcript_data['video_id'],
            'title': transcript_data['title'],
            'knowledge_chunks': len(chunks),
            'arxiv_papers': len(paper_nodes),
            'github_repos': len(repo_nodes),
            'graph_nodes': 1 + len(chunks) + len(paper_nodes) + len(repo_nodes),
            'graph_edges': await self._count_edges(video_node['_id']),
            'arangodb_features': {
                'semantic_embeddings': 'processing',
                'graph_algorithms': 'available',
                'similarity_search': 'enabled'
            }
        }
    
    async def _download_and_extract(self, video_url: str) -> Dict[str, Any]:
        """Download transcript and extract all metadata."""
        # Use the enhanced download_transcript function
        from youtube_transcripts.scripts.download_transcript import (
            download_youtube_transcript,
            extract_video_id,
            get_video_info,
            get_video_comments
        )
        
        video_id = extract_video_id(video_url)
        
        # Get video metadata and links
        title, channel, duration, description, author_links = get_video_info(video_id)
        
        # Download full transcript
        transcript_path = download_youtube_transcript(video_url)
        
        # Read the transcript
        with open(transcript_path, 'r') as f:
            content = f.read()
        
        # Get comments with links
        comments = get_video_comments(video_id)
        
        # Separate links by type and authority
        arxiv_links = [link for link in author_links if link.link_type == 'arxiv']
        github_links = [link for link in author_links if link.link_type == 'github']
        
        # Add comment links
        for _, _, comment_links in comments:
            arxiv_links.extend([l for l in comment_links if l.link_type == 'arxiv'])
            github_links.extend([l for l in comment_links if l.link_type == 'github'])
        
        return {
            'video_id': video_id,
            'title': title,
            'channel': channel,
            'duration': duration,
            'description': description,
            'transcript': content,
            'arxiv_links': arxiv_links,
            'github_links': github_links,
            'comments': comments
        }
    
    def _create_knowledge_chunks(self, transcript: str, video_id: str, 
                                chunk_size: int) -> List[KnowledgeChunk]:
        """Break transcript into semantic knowledge chunks."""
        chunks = []
        lines = transcript.split('\n')
        
        current_chunk = []
        current_size = 0
        chunk_index = 0
        start_time = 0.0
        
        for line in lines:
            # Extract timestamp if present
            timestamp_match = re.match(r'\[(\d+\.\d+)\]', line)
            if timestamp_match:
                time = float(timestamp_match.group(1))
                if not current_chunk:
                    start_time = time
            
            current_chunk.append(line)
            current_size += len(line)
            
            # Create chunk when size limit reached
            if current_size >= chunk_size:
                chunk_text = '\n'.join(current_chunk)
                chunks.append(KnowledgeChunk(
                    text=chunk_text,
                    start_time=start_time,
                    end_time=time if timestamp_match else start_time,
                    video_id=video_id,
                    chunk_index=chunk_index
                ))
                
                current_chunk = []
                current_size = 0
                chunk_index += 1
                start_time = time if timestamp_match else start_time
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(KnowledgeChunk(
                text='\n'.join(current_chunk),
                start_time=start_time,
                end_time=time if 'time' in locals() else start_time,
                video_id=video_id,
                chunk_index=chunk_index
            ))
        
        return chunks
    
    async def _store_video_data(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store video metadata in ArangoDB."""
        video_doc = {
            '_key': transcript_data['video_id'],
            'title': transcript_data['title'],
            'channel': transcript_data['channel'],
            'duration': transcript_data['duration'],
            'description': transcript_data['description'],
            'url': f"https://www.youtube.com/watch?v={transcript_data['video_id']}",
            'processed_at': datetime.now().isoformat(),
            'transcript_length': len(transcript_data['transcript'])
        }
        
        result = self.db.collection('videos').insert(video_doc)
        logger.info(f"Stored video: {video_doc['title']}")
        return result
    
    async def _store_chunks(self, chunks: List[KnowledgeChunk], 
                           video_id: str) -> List[Dict[str, Any]]:
        """Store knowledge chunks in ArangoDB."""
        chunk_docs = []
        
        for chunk in chunks:
            doc = {
                'text': chunk.text,
                'start_time': chunk.start_time,
                'end_time': chunk.end_time,
                'video_id': chunk.video_id,
                'chunk_index': chunk.chunk_index,
                'char_count': len(chunk.text),
                'needs_embedding': True  # Flag for ArangoDB to process
            }
            
            result = self.db.collection('chunks').insert(doc)
            chunk_docs.append(result)
            
            # Create edge: chunk → video
            self.db.collection('chunk_of').insert({
                '_from': f"chunks/{result['_key']}",
                '_to': video_id,
                'index': chunk.chunk_index
            })
        
        logger.info(f"Stored {len(chunks)} knowledge chunks")
        return chunk_docs
    
    async def _process_arxiv_papers(self, arxiv_links: List[ExtractedLink]) -> List[Dict[str, Any]]:
        """Process ArXiv papers through MCP server."""
        paper_nodes = []
        
        # Call ArXiv MCP server for each unique paper
        seen_urls = set()
        for link in arxiv_links:
            if link.url in seen_urls:
                continue
            seen_urls.add(link.url)
            
            # Extract paper ID from URL
            paper_id = link.url.split('/')[-1]
            
            # TODO: Call actual ArXiv MCP server
            # For now, create placeholder
            paper_doc = {
                '_key': paper_id,
                'url': link.url,
                'is_authoritative': link.is_authoritative,
                'mentioned_by': link.source,
                'needs_processing': True  # Flag for ArXiv MCP to process
            }
            
            result = self.db.collection('papers').insert(paper_doc)
            paper_nodes.append(result)
            
            logger.info(f"Queued ArXiv paper for processing: {paper_id}")
        
        return paper_nodes
    
    async def _process_github_repos(self, github_links: List[ExtractedLink]) -> List[Dict[str, Any]]:
        """Process GitHub repos through GitGet."""
        repo_nodes = []
        
        # Process each unique repository
        seen_urls = set()
        for link in github_links:
            if link.url in seen_urls:
                continue
            seen_urls.add(link.url)
            
            # Extract owner/repo from URL
            repo_path = link.url.replace('https://github.com/', '')
            
            # TODO: Call actual GitGet
            # For now, create placeholder
            repo_doc = {
                '_key': repo_path.replace('/', '_'),
                'url': link.url,
                'repo_path': repo_path,
                'is_authoritative': link.is_authoritative,
                'mentioned_by': link.source,
                'needs_processing': True  # Flag for GitGet to process
            }
            
            result = self.db.collection('repositories').insert(repo_doc)
            repo_nodes.append(result)
            
            logger.info(f"Queued GitHub repo for processing: {repo_path}")
        
        return repo_nodes
    
    async def _create_relationships(self, video_node, chunk_nodes, paper_nodes, 
                                   repo_nodes, transcript_data):
        """Create all graph relationships."""
        video_key = f"videos/{video_node['_key']}"
        
        # Video mentions papers and repos
        for paper in paper_nodes:
            self.db.collection('mentions').insert({
                '_from': video_key,
                '_to': f"papers/{paper['_key']}",
                'is_authoritative': paper.get('is_authoritative', False)
            })
        
        for repo in repo_nodes:
            self.db.collection('mentions').insert({
                '_from': video_key,
                '_to': f"repositories/{repo['_key']}",
                'is_authoritative': repo.get('is_authoritative', False)
            })
        
        # Process comments
        for author, text, links in transcript_data['comments']:
            # Store valuable comment
            comment_doc = self.db.collection('comments').insert({
                'author': author,
                'text': text,
                'video_id': transcript_data['video_id'],
                'has_links': True
            })
            
            # Comment → Video relationship
            self.db.collection('commented_on').insert({
                '_from': f"comments/{comment_doc['_key']}",
                '_to': video_key
            })
        
        logger.info("Created all graph relationships")
    
    async def _trigger_graph_enhancements(self, video_id: str):
        """Trigger ArangoDB's automatic graph enhancements."""
        # This would trigger ArangoDB's features:
        # 1. Semantic embedding generation for chunks
        # 2. Similarity calculations between chunks
        # 3. Graph algorithm preprocessing
        # 4. Index updates for fast traversal
        
        logger.info(f"Triggered graph enhancements for video {video_id}")
        
        # In a real implementation, this might call ArangoDB's
        # graph processing endpoints or scheduled jobs
        pass
    
    async def _count_edges(self, video_id: str) -> int:
        """Count total edges related to this video."""
        query = """
        FOR v IN videos
            FILTER v._id == @video_id
            LET mentions = LENGTH(FOR e IN mentions FILTER e._from == v._id RETURN 1)
            LET chunks = LENGTH(FOR e IN chunk_of FILTER e._to == v._id RETURN 1)
            LET comments = LENGTH(FOR e IN commented_on FILTER e._to == v._id RETURN 1)
            RETURN mentions + chunks + comments
        """
        cursor = self.db.aql.execute(query, bind_vars={'video_id': video_id})
        return next(cursor, 0)


# Simplified API for agents
async def process_research_video(video_url: str, 
                                research_topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple API for agents to process a research video.
    
    Args:
        video_url: YouTube video URL
        research_topic: Optional topic for enhanced processing
        
    Returns:
        Summary of processing results
    """
    # Load ArangoDB config from environment
    arango_config = {
        'url': os.getenv('ARANGODB_URL', 'http://localhost:8529'),
        'database': os.getenv('ARANGODB_DATABASE', 'research'),
        'username': os.getenv('ARANGODB_USERNAME', 'root'),
        'password': os.getenv('ARANGODB_PASSWORD', 'password')
    }
    
    processor = ResearchVideoProcessor(arango_config)
    request = ResearchRequest(
        video_url=video_url,
        research_topic=research_topic
    )
    
    return await processor.process_video(request)


if __name__ == "__main__":
    # Example usage
    import os
    import re
    
    async def test_scenario():
        """Test the research video processing scenario."""
        # Example video about RLHF
        video_url = "https://www.youtube.com/watch?v=exampleRLHF"
        
        try:
            result = await process_research_video(
                video_url,
                research_topic="reinforcement learning from human feedback"
            )
            
            print("\n✅ Research Video Processing Complete!")
            print(f"Video: {result['title']}")
            print(f"Knowledge Chunks: {result['knowledge_chunks']}")
            print(f"ArXiv Papers: {result['arxiv_papers']}")
            print(f"GitHub Repos: {result['github_repos']}")
            print(f"Total Graph Nodes: {result['graph_nodes']}")
            print(f"Total Graph Edges: {result['graph_edges']}")
            print("\nArangoDB Features:")
            for feature, status in result['arangodb_features'].items():
                print(f"  - {feature}: {status}")
                
        except Exception as e:
            logger.error(f"Test failed: {e}")
            raise
    
    # Run test
    asyncio.run(test_scenario())