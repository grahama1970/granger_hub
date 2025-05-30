# Level 0 Test Scenarios - Single Module Operations

These scenarios test claude-module-communicator's ability to invoke single modules with various CLI parameters.

## MCP Screenshot Module (12 scenarios)

1. `claude-comm screenshot --output dashboard.png --quality 95`
2. `claude-comm screenshot --region right --output right_panel.jpg --quality 80`
3. `claude-comm screenshot --url https://d3js.org --wait 5 --output d3_homepage.png`
4. `claude-comm screenshot --describe --prompt "Identify all UI elements"`
5. `claude-comm screenshot --region center --describe --prompt "What chart type is shown?"`
6. `claude-comm screenshot --region left --quality 60 --format webp`
7. `claude-comm screenshot --url https://github.com --selector ".Header" --output header.png`
8. `claude-comm screenshot --region bottom --describe --model "gemini-pro-vision"`
9. `claude-comm screenshot --fullpage --url https://arxiv.org --output arxiv_full.png`
10. `claude-comm screenshot --element "#main-content" --quality 100`
11. `claude-comm screenshot --multi-monitor --screen 2 --output screen2.png`
12. `claude-comm screenshot --annotate --color red --text "Important section"`

## ArangoDB Module (10 scenarios)

13. `claude-comm send arangodb memory create --user "How do transformers work?" --agent "Transformers use attention" --tags "ml,nlp"`
14. `claude-comm send arangodb memory search --query "machine learning" --limit 10 --algorithm semantic`
15. `claude-comm send arangodb graph visualize --collection memories --layout force-directed --output graph.html`
16. `claude-comm send arangodb graph communities --min-size 3 --algorithm louvain`
17. `claude-comm send arangodb qa generate --source memories --count 50 --difficulty medium`
18. `claude-comm send arangodb contradictions find --threshold 0.8 --include-context`
19. `claude-comm send arangodb episode create --title "ML Session" --description "Deep dive"`
20. `claude-comm send arangodb temporal analyze --start "2024-01-01" --end "2024-12-31"`
21. `claude-comm send arangodb graph shortest-path --from "node1" --to "node2"`
22. `claude-comm send arangodb compaction run --collections "memories,episodes"`

## Claude Max Proxy / LLM Call (8 scenarios)

23. `claude-comm send claude_max_proxy ask --model "gemini/gemini-2.0-flash-exp" --prompt "Explain quantum entanglement"`
24. `claude-comm send claude_max_proxy ask --model "claude-3-opus-20240229" --prompt "Write a haiku" --temperature 0.9`
25. `claude-comm send claude_max_proxy compare --models "gpt-4,claude-3-opus,gemini-pro" --prompt "Best data structure?"`
26. `claude-comm send claude_max_proxy summarize --model "gemini/gemini-2.0-flash-exp" --text-file "doc.txt" --window-size 4000`
27. `claude-comm send claude_max_proxy dialogue --model "claude-3-sonnet-20240229" --prompt "Design a system"`
28. `claude-comm send claude_max_proxy translate --model "gpt-4" --text "Bonjour" --to "es" --from "fr"`
29. `claude-comm send claude_max_proxy code-review --model "claude-3-opus" --file "main.py" --focus "security"`
30. `claude-comm send claude_max_proxy explain --model "gemini-pro" --code "def fib(n): return fib(n-1)+fib(n-2)"`

## Marker Module (8 scenarios)

31. `claude-comm send marker convert --input paper.pdf --output paper.md`
32. `claude-comm send marker convert --input report.pdf --extract-tables --table-method surya`
33. `claude-comm send marker convert --input doc.pdf --claude-config accuracy --verify-sections`
34. `claude-comm send marker batch --input-dir ./pdfs --output-dir ./markdown --priority high --max-workers 4`
35. `claude-comm send marker convert --input manual.pdf --pages 10-25 --output chapter2.md`
36. `claude-comm send marker extract-images --input diagram.pdf --output-dir ./images --format png`
37. `claude-comm send marker validate --input processed.md --check-structure --fix-formatting`
38. `claude-comm send marker merge --inputs "part1.md,part2.md" --output complete.md`

## YouTube Transcripts (7 scenarios)

39. `claude-comm send youtube_transcripts search --query "machine learning" --after "2024-01-01" --max-results 20`
40. `claude-comm send youtube_transcripts search --channel "3Blue1Brown" --query "linear algebra"`
41. `claude-comm send youtube_transcripts search --query "quantum computing" --widen --max-levels 3`
42. `claude-comm send youtube_transcripts fetch --video-id "dQw4w9WgXcQ" --format json`
43. `claude-comm send youtube_transcripts export --query "climate change" --output results.csv`
44. `claude-comm send youtube_transcripts analyze --video-id "abc123" --extract-topics --sentiment`
45. `claude-comm send youtube_transcripts batch-fetch --channel-id "UC123" --last-n 50`

## ArXiv (7 scenarios)

46. `claude-comm send arxiv search --query "transformer architecture" --categories "cs.LG,cs.CL" --max-results 50`
47. `claude-comm send arxiv find-support --hypothesis "Attention is all you need" --type bolster`
48. `claude-comm send arxiv find-support --hypothesis "Larger models always better" --type contradict --all`
49. `claude-comm send arxiv download --paper-id "2312.12345" --convert-to-markdown`
50. `claude-comm send arxiv search --query "diffusion models" --date-from "2024-01-01" --date-to "2024-12-31"`
51. `claude-comm send arxiv related --paper-id "2401.12345" --method "citation" --depth 2`
52. `claude-comm send arxiv trending --category "cs.AI" --period "week" --min-citations 10`

Total: 52 Level 0 scenarios covering all major modules with diverse parameter combinations.
