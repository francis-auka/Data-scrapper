import { useState, useEffect } from 'react'
import axios from 'axios'
import { Send, Loader2, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

export default function ScraperTab() {
    const [urls, setUrls] = useState('')
    const [loading, setLoading] = useState(false)
    const [tasks, setTasks] = useState([])
    const [productMode, setProductMode] = useState(false)
    const [maxPages, setMaxPages] = useState(3)

    const handleScrape = async () => {
        if (!urls.trim()) return
        setLoading(true)
        try {
            const urlList = urls.split('\n').filter(u => u.trim())

            let response
            if (productMode) {
                // Use product scraper
                response = await axios.post(`${API_BASE}/scrape-products`, {
                    urls: urlList,
                    max_pages: maxPages,
                    auto_detect: false
                })
            } else {
                // Use regular scraper
                response = await axios.post(`${API_BASE}/scrape`, { urls: urlList })
            }

            setUrls('')
            // Poll for task status
            pollTask(response.data.task_id)
        } catch (error) {
            console.error('Scrape failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const pollTask = async (taskId) => {
        const interval = setInterval(async () => {
            try {
                const response = await axios.get(`${API_BASE}/tasks/${taskId}`)
                const task = response.data
                setTasks(prev => {
                    const index = prev.findIndex(t => t.id === taskId)
                    if (index > -1) {
                        const newTasks = [...prev]
                        newTasks[index] = task
                        return newTasks
                    }
                    return [task, ...prev]
                })

                if (task.status === 'completed' || task.status === 'failed') {
                    clearInterval(interval)
                }
            } catch (error) {
                clearInterval(interval)
            }
        }, 2000)
    }

    const downloadResults = (task) => {
        if (!task.result || task.result.length === 0) {
            alert('No data to download')
            return
        }

        // Convert results to CSV
        const results = task.result
        const headers = Object.keys(results[0])
        const csvContent = [
            headers.join(','),
            ...results.map(row =>
                headers.map(header => {
                    const value = row[header] || ''
                    // Escape values containing commas or quotes
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        return `"${value.replace(/"/g, '""')}"`
                    }
                    return value
                }).join(',')
            )
        ].join('\n')

        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `scraped_data_${task.id.slice(0, 8)}_${new Date().toISOString().split('T')[0]}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
    }

    return (
        <div className="p-6 space-y-8">
            <div className="space-y-4">
                <label className="block text-sm font-medium text-gray-400">
                    Enter URLs (one per line)
                </label>
                <textarea
                    value={urls}
                    onChange={(e) => setUrls(e.target.value)}
                    placeholder="https://example.com/products"
                    className="w-full h-32 bg-gray-800 border border-gray-700 rounded-xl p-4 text-gray-100 focus:ring-2 focus:ring-blue-600 focus:border-transparent transition-all resize-none"
                />

                {/* Product Scraping Options */}
                <div className="flex items-center gap-6 p-4 bg-gray-800/50 border border-gray-700 rounded-xl">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={productMode}
                            onChange={(e) => setProductMode(e.target.checked)}
                            className="w-4 h-4 rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-blue-600 focus:ring-offset-gray-900"
                        />
                        <span className="text-sm text-gray-300 font-medium">
                            🛍️ Product-Level Scraping (JS rendering, pagination)
                        </span>
                    </label>

                    {productMode && (
                        <div className="flex items-center gap-2">
                            <label className="text-xs text-gray-500">Max Pages:</label>
                            <input
                                type="number"
                                min="1"
                                max="10"
                                value={maxPages}
                                onChange={(e) => setMaxPages(parseInt(e.target.value))}
                                className="w-16 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-gray-200 focus:ring-2 focus:ring-blue-600"
                            />
                        </div>
                    )}
                </div>

                <button
                    onClick={handleScrape}
                    disabled={loading || !urls.trim()}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-900/20"
                >
                    {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                    {productMode ? 'Start Product Scraping' : 'Start Scraping'}
                </button>
            </div>

            <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white">Recent Tasks</h3>
                <div className="space-y-3">
                    {tasks.length === 0 && (
                        <div className="text-center py-10 border-2 border-dashed border-gray-800 rounded-2xl text-gray-500">
                            No tasks yet. Start scraping to see progress.
                        </div>
                    )}
                    {tasks.map((task) => (
                        <div key={task.id} className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                {task.status === 'running' && <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />}
                                {task.status === 'completed' && <CheckCircle className="w-5 h-5 text-green-400" />}
                                {task.status === 'failed' && <AlertCircle className="w-5 h-5 text-red-400" />}
                                <div>
                                    <div className="font-medium text-gray-200">Task {task.id.slice(0, 8)}</div>
                                    <div className="text-xs text-gray-500">
                                        {task.metadata.urls?.length} URLs • {task.status}
                                        {task.status === 'completed' && task.result && ` • ${task.result.length} results`}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-6">
                                <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-blue-600 transition-all duration-500"
                                        style={{ width: `${task.progress}%` }}
                                    />
                                </div>
                                {task.status === 'completed' && (
                                    <button
                                        onClick={() => downloadResults(task)}
                                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-all"
                                        title="Download scraped data as CSV"
                                    >
                                        <ExternalLink className="w-4 h-4" />
                                        Download CSV
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
