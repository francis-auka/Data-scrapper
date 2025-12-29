import { useState } from 'react'
import ScraperTab from './components/ScraperTab'
import ProcessorTab from './components/ProcessorTab'
import { Layout, Database, Search, FileText, Settings } from 'lucide-react'

function App() {
  const [activeTab, setActiveTab] = useState('scraper')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-gray-900 border-r border-gray-800 p-6 flex flex-col">
        <div className="flex items-center gap-3 mb-10 px-2">
          <div className="p-2 bg-blue-600 rounded-lg">
            <Database className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight">DataScrapper</h1>
        </div>

        <nav className="flex-1 space-y-2">
          <button
            onClick={() => setActiveTab('scraper')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'scraper'
                ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
          >
            <Search className="w-5 h-5" />
            <span className="font-medium">Web Scraping</span>
          </button>
          <button
            onClick={() => setActiveTab('processor')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'processor'
                ? 'bg-blue-600/10 text-blue-400 border border-blue-600/20'
                : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
          >
            <FileText className="w-5 h-5" />
            <span className="font-medium">Data Processing</span>
          </button>
        </nav>

        <div className="mt-auto pt-6 border-t border-gray-800">
          <div className="flex items-center gap-3 px-4 py-3 text-gray-400 hover:text-gray-200 cursor-pointer transition-colors">
            <Settings className="w-5 h-5" />
            <span className="font-medium">Settings</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8 max-w-7xl mx-auto">
        <header className="mb-10">
          <h2 className="text-3xl font-bold text-white mb-2">
            {activeTab === 'scraper' ? 'Web Scraping Module' : 'Data Processing Module'}
          </h2>
          <p className="text-gray-400">
            {activeTab === 'scraper'
              ? 'Extract structured data from any public URL or search by keywords.'
              : 'Clean, filter, merge and summarize your datasets with ease.'}
          </p>
        </header>

        <div className="bg-gray-900 rounded-2xl border border-gray-800 shadow-xl overflow-hidden">
          {activeTab === 'scraper' ? <ScraperTab /> : <ProcessorTab />}
        </div>
      </main>
    </div>
  )
}

export default App
