import { useState, useEffect } from 'react';
import { Play, Activity, CheckCircle2, XCircle, RefreshCw, Loader2, Globe, Brain } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function App() {
  const [url, setUrl] = useState('');
  const [objective, setObjective] = useState('');
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [state, setState] = useState(null);
  const [isLaunching, setIsLaunching] = useState(false);

  const startScrape = async (e) => {
    e.preventDefault();
    if (!url || !objective) return;
    
    // Reset all state for a fresh run
    setJobId(null);
    setState(null);
    setStatus(null);
    setIsLaunching(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, objective })
      });
      const data = await res.json();
      setJobId(data.job_id);
      setStatus('running');
    } catch (err) {
      console.error(err);
      setStatus('failed');
    } finally {
      setIsLaunching(false);
    }
  };

  useEffect(() => {
    let interval;
    // Keep polling until we have scraped_data or a failure
    if (jobId && status && status !== 'failed') {
      const shouldPoll = status !== 'done' || (status === 'done' && !state?.scraped_data);
      if (shouldPoll) {
        interval = setInterval(async () => {
          try {
            const res = await fetch(`${API_BASE_URL}/api/scrape/${jobId}`);
            if (!res.ok) return;
            const data = await res.json();
            setState(data);
            setStatus(data.status);
          } catch (err) {
            console.error(err);
          }
        }, 2000);
      }
    }
    return () => clearInterval(interval);
  }, [jobId, status, state?.scraped_data]);

  const getStepStatusColor = (stepIdx) => {
    if (!state) return 'bg-slate-600';
    if (state.current_step_index > stepIdx) return 'bg-green-500';
    if (state.current_step_index === stepIdx) {
      if (status === 'correcting') return 'bg-amber-500 animate-pulse';
      if (status === 'running') return 'bg-blue-500 animate-pulse';
      return 'bg-blue-500';
    }
    return 'bg-slate-600';
  };

  const getStepLabel = (step) => {
    const action = step.action;
    if (action === 'extract') return 'Extract data from page';
    if (action === 'extract_page_content') return 'Save page content to memory';
    if (action === 'finish_and_synthesize') return 'Synthesize final answer from all crawled pages';
    if (action === 'click') return `Click: ${step.selector}`;
    if (action === 'waitForSelector') return `Wait for: ${step.selector}`;
    if (action === 'type_text') return `Type "${step.text}" into ${step.selector}`;
    if (action === 'navigate') return `Navigate to ${step.url}`;
    return JSON.stringify(step);
  };

  const getStatusDisplay = () => {
    if (!status) return null;
    
    // If status is "done" but no scraped_data yet, show "Extracting..."
    if (status === 'done' && !state?.scraped_data) {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-purple-900/50 text-sm font-medium text-purple-300 border border-purple-500/30">
          <Brain size={16} className="animate-pulse" /> Extracting...
        </div>
      );
    }
    if (status === 'done' && state?.scraped_data) {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-900/50 text-sm font-medium text-green-300 border border-green-500/30">
          <CheckCircle2 size={16} /> Completed
        </div>
      );
    }
    if (status === 'running') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-900/50 text-sm font-medium text-blue-300 border border-blue-500/30">
          <Activity size={16} className="animate-pulse" /> Running
        </div>
      );
    }
    if (status === 'correcting') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-900/50 text-sm font-medium text-amber-300 border border-amber-500/30">
          <RefreshCw size={16} className="animate-spin" /> Self-Correcting
        </div>
      );
    }
    if (status === 'planning') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-900/50 text-sm font-medium text-indigo-300 border border-indigo-500/30">
          <Brain size={16} className="animate-pulse" /> Planning
        </div>
      );
    }
    if (status === 'failed') {
      return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-900/50 text-sm font-medium text-red-300 border border-red-500/30">
          <XCircle size={16} /> Failed
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen p-8 max-w-6xl mx-auto">
      <header className="mb-8 border-b border-slate-800 pb-4">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
          Self-Correcting OSINT Scraper
        </h1>
        <p className="text-slate-400 mt-2">Agentic workflow that heals its own selectors using visual DOM analysis.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Input Panel */}
        <div className="col-span-1 bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl h-fit">
          <h2 className="text-xl font-semibold mb-4 text-slate-200">New Task</h2>
          <form onSubmit={startScrape} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Target URL</label>
              <input 
                type="url" 
                value={url} 
                onChange={e => setUrl(e.target.value)}
                placeholder="https://news.ycombinator.com"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Objective & Schema</label>
              <textarea 
                value={objective} 
                onChange={e => setObjective(e.target.value)}
                rows={4}
                placeholder="Extract the top 5 articles with schema: [{title, link, points}]"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
            </div>
            <button 
              type="submit"
              disabled={isLaunching || (status === 'running' || status === 'correcting')}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition disabled:opacity-50"
            >
              {isLaunching ? (
                <><Loader2 size={18} className="animate-spin" /> Launching...</>
              ) : (
                <><Play size={18} /> Launch Agent</>
              )}
            </button>
          </form>
        </div>

        {/* Live Visualizer */}
        <div className="col-span-2 space-y-6">
          <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl min-h-[300px]">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-200">Execution Flow</h2>
              {getStatusDisplay()}
            </div>

            {state ? (
              <div className="space-y-4 relative">
                {/* Steps List */}
                <div className="border-l-2 border-slate-700 ml-3 pl-6 space-y-6">
                  {state.steps?.map((step, idx) => (
                    <div key={idx} className="relative">
                      <div className={`absolute -left-[35px] w-4 h-4 rounded-full border-4 border-slate-800 ${getStepStatusColor(idx)}`}>
                      </div>
                      <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700/50">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">
                          Step {idx + 1}
                        </span>
                        <p className="text-sm text-blue-300">{getStepLabel(step)}</p>
                      </div>
                    </div>
                  ))}
                </div>
                
                {state.error_message && status === 'failed' && (
                  <div className="mt-4 bg-red-900/20 border border-red-500/50 text-red-300 p-4 rounded-lg text-sm flex gap-3">
                    <XCircle size={20} className="shrink-0" />
                    <p>{state.error_message}</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm py-16">
                <div className="text-center space-y-2">
                  <Globe size={32} className="mx-auto text-slate-600" />
                  <p>Enter a URL and objective, then launch the agent.</p>
                </div>
              </div>
            )}
          </div>

          {/* Results Block */}
          {state?.scraped_data && (
            <div className="space-y-6">
              {state.scraped_data.response && (
                <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl relative overflow-hidden">
                  <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>
                  <h2 className="text-xl font-semibold mb-4 text-indigo-300 flex items-center gap-2">
                    <Brain size={20} /> Agent Response
                  </h2>
                  <div className="prose prose-invert max-w-none text-slate-200 space-y-4 text-sm leading-relaxed whitespace-pre-line bg-slate-900/40 p-4 rounded-lg border border-slate-700/30">
                    {state.scraped_data.response}
                  </div>
                </div>
              )}
              
              <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl overflow-auto">
                <h2 className="text-xl font-semibold mb-4 text-green-400 flex items-center gap-2">
                  <CheckCircle2 size={20} /> {state.scraped_data.response ? "Structured Data Payload" : "Extracted Payload"}
                </h2>
                <pre className="bg-slate-900 p-4 rounded-lg text-sm text-green-300 overflow-x-auto border border-slate-700/50 max-h-[500px] overflow-y-auto font-mono">
                  {JSON.stringify(state.scraped_data.structured_data || state.scraped_data, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
