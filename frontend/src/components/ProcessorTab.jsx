import { useState, useMemo } from 'react'
import axios from 'axios'
import {
    Upload, FileText, Download, Trash2, Filter, BarChart2,
    Settings, Plus, X, Check, ChevronDown, ChevronUp,
    PieChart as PieChartIcon, BarChart as BarChartIcon, LineChart as LineChartIcon,
    Sparkles, Lightbulb
} from 'lucide-react'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    LineChart, Line, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts'
import { toPng } from 'html-to-image'

const API_BASE = 'http://localhost:8000/api'
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

export default function ProcessorTab() {
    const [file, setFile] = useState(null)
    const [data, setData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [previewRows, setPreviewRows] = useState(100)
    const [activeModal, setActiveModal] = useState(null) // 'clean', 'filter', 'summarize', 'visualize', 'auto-clean', 'explain'

    // Processing States
    const [filterConditions, setFilterConditions] = useState([{ column: '', operator: 'contains', value: '' }])
    const [filterLogic, setFilterLogic] = useState('AND')
    const [cleanOptions, setCleanOptions] = useState({ deduplicate: true, trim: true, normalize_columns: false, handle_missing: false })
    const [summaryConfig, setSummaryConfig] = useState({ group_by: [], aggregations: [] })
    const [chartConfig, setChartConfig] = useState({
        type: 'bar',
        xAxis: '',
        yAxes: [], // Changed to array for multi-dataset support
        stack: false,
        autoSuggest: true
    })

    // Auto Clean & Explain States
    const [cleaningReport, setCleaningReport] = useState(null)
    const [datasetExplanation, setDatasetExplanation] = useState(null)


    const handleUpload = async (e) => {
        const uploadedFile = e.target.files[0]
        if (!uploadedFile) return

        setLoading(true)
        const formData = new FormData()
        formData.append('file', uploadedFile)

        try {
            const response = await axios.post(`${API_BASE}/upload?preview_rows=${previewRows}`, formData)
            console.log('📤 Upload Response:', response.data)
            console.log('📊 Columns:', response.data.columns)
            console.log('🔍 Preview Sample:', response.data.preview.slice(0, 2))

            setData(response.data)
            setFile(uploadedFile)

            // Auto-suggest initial configuration
            if (response.data.columns.length >= 2) {
                const xCol = response.data.columns[0].name
                const numericCols = response.data.columns.filter(c => c.type === 'numeric').map(c => c.name)
                const dateCols = response.data.columns.filter(c => c.type === 'datetime').map(c => c.name)

                console.log('🔢 Numeric Columns:', numericCols)
                console.log('📅 Date Columns:', dateCols)

                let suggestedType = 'bar'
                let suggestedX = xCol
                let suggestedY = numericCols.length > 0 ? [numericCols[0]] : []

                if (dateCols.length > 0) {
                    suggestedType = 'line'
                    suggestedX = dateCols[0]
                } else if (numericCols.length === 1 && response.data.total_rows < 10) {
                    suggestedType = 'pie'
                }

                console.log('💡 Suggested Chart Config:', { type: suggestedType, xAxis: suggestedX, yAxes: suggestedY })

                setChartConfig({
                    type: suggestedType,
                    xAxis: suggestedX,
                    yAxes: suggestedY,
                    stack: false,
                    autoSuggest: true
                })
            }
        } catch (error) {
            console.error('Upload failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const applyProcessing = async (type, params) => {
        if (!data) return
        setLoading(true)
        try {
            const operation = { type, params }
            const response = await axios.post(`${API_BASE}/process?preview_rows=${previewRows}`, {
                data_id: data.data_id,
                operations: [operation]
            })
            setData(response.data)
            setActiveModal(null)
        } catch (error) {
            console.error('Processing failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleExport = async () => {
        if (!data) return
        try {
            const response = await axios.get(`${API_BASE}/export/${data.data_id}?format=csv`)
            const blob = new Blob([response.data.content], { type: 'text/csv' })
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = response.data.filename
            a.click()
        } catch (error) {
            console.error('Export failed:', error)
        }
    }

    const handleAutoClean = async () => {
        if (!data) return
        setLoading(true)
        try {
            const response = await axios.post(`${API_BASE}/auto-clean`, {
                data_id: data.data_id
            })
            setCleaningReport(response.data.cleaning_report)
            // Update data with cleaned version
            setData({
                data_id: response.data.cleaned_data_id,
                preview: response.data.preview,
                columns: response.data.columns,
                total_rows: response.data.total_rows
            })
            setActiveModal('auto-clean')
        } catch (error) {
            console.error('Auto-clean failed:', error)
            alert('Failed to clean data. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleExplainDataset = async () => {
        if (!data) return
        setLoading(true)
        try {
            const response = await axios.post(`${API_BASE}/explain-dataset`, {
                data_id: data.data_id
            })
            setDatasetExplanation(response.data)
            setActiveModal('explain')
        } catch (error) {
            console.error('Explain dataset failed:', error)
            alert('Failed to explain dataset. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const downloadCleaningReport = (format) => {
        if (!cleaningReport) return

        let content, filename, mimeType

        if (format === 'json') {
            content = JSON.stringify(cleaningReport, null, 2)
            filename = 'cleaning_report.json'
            mimeType = 'application/json'
        } else {
            // TXT format
            content = `DATA CLEANING REPORT\n\n`
            content += `Original Rows: ${cleaningReport.original_rows}\n`
            content += `Final Rows: ${cleaningReport.final_rows}\n`
            content += `Original Columns: ${cleaningReport.original_columns}\n`
            content += `Final Columns: ${cleaningReport.final_columns}\n\n`
            content += `CHANGES:\n`
            cleaningReport.summary.forEach(item => {
                content += `- ${item}\n`
            })
            filename = 'cleaning_report.txt'
            mimeType = 'text/plain'
        }

        const blob = new Blob([content], { type: mimeType })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        a.click()
        window.URL.revokeObjectURL(url)
    }

    const exportChart = async () => {
        const node = document.getElementById('chart-container');
        if (!node) return;
        try {
            const dataUrl = await toPng(node, { backgroundColor: '#111827', cacheBust: true });
            const link = document.createElement('a');
            link.download = `chart-${new Date().getTime()}.png`;
            link.href = dataUrl;
            link.click();
        } catch (err) {
            console.error('Export failed', err);
        }
    };

    const renderChart = () => {
        console.log('=== RENDER CHART DEBUG ===')
        console.log('Chart Config:', chartConfig)
        console.log('Data exists:', !!data)
        console.log('Data preview length:', data?.preview?.length)

        if (!data || !chartConfig.xAxis || chartConfig.yAxes.length === 0) {
            console.log('❌ Missing required config:', {
                hasData: !!data,
                xAxis: chartConfig.xAxis,
                yAxesCount: chartConfig.yAxes.length
            })
            return (
                <div className="flex flex-col items-center justify-center h-[400px] text-gray-500">
                    <BarChartIcon className="w-12 h-12 mb-2 opacity-20" />
                    <p>Select X and at least one Y axis to visualize data</p>
                    <p className="text-xs mt-2">Debug: {!data ? 'No data' : !chartConfig.xAxis ? 'No X-axis' : 'No Y-axes selected'}</p>
                </div>
            )
        }


        console.log('✅ Processing chart data...')

        // Check if any Y-axes are non-numeric (need counting)
        const yAxisTypes = chartConfig.yAxes.map(y => {
            const col = data.columns.find(c => c.name === y);
            return { name: y, type: col?.type || 'string', isNumeric: col?.type === 'numeric' };
        });

        console.log('Y-Axis Types:', yAxisTypes);

        let chartData;

        // If all Y-axes are numeric, process normally
        if (yAxisTypes.every(y => y.isNumeric)) {
            chartData = data.preview.slice(0, 20).map(row => {
                const newRow = { ...row };
                chartConfig.yAxes.forEach(y => {
                    newRow[y] = parseFloat(row[y]) || 0;
                });
                return newRow;
            });
        } else {
            // If any Y-axis is categorical, we need to aggregate
            // For categorical Y-axes, count occurrences per X-axis value
            const aggregated = {};

            data.preview.forEach(row => {
                const xValue = row[chartConfig.xAxis];
                if (!aggregated[xValue]) {
                    aggregated[xValue] = {};
                    chartConfig.yAxes.forEach(y => {
                        aggregated[xValue][y] = 0;
                    });
                }

                chartConfig.yAxes.forEach(y => {
                    const yType = yAxisTypes.find(yt => yt.name === y);
                    if (yType.isNumeric) {
                        aggregated[xValue][y] += parseFloat(row[y]) || 0;
                    } else {
                        // For categorical, just count occurrences
                        aggregated[xValue][y] += 1;
                    }
                });
            });

            chartData = Object.entries(aggregated).map(([xVal, yVals]) => ({
                [chartConfig.xAxis]: xVal,
                ...yVals
            })).slice(0, 20);
        }

        console.log('Chart Data Sample:', chartData.slice(0, 3))
        console.log('Y-Axes Values Sample:', chartConfig.yAxes.map(y => ({
            column: y,
            values: chartData.slice(0, 3).map(row => row[y])
        })))

        const commonProps = {
            width: '100%',
            height: '100%',
            data: chartData,
            margin: { top: 20, right: 30, left: 20, bottom: 60 }
        };

        return (
            <div className="space-y-4">
                <div className="flex justify-end">
                    <button
                        onClick={exportChart}
                        className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs font-bold rounded-lg transition-all"
                    >
                        <Download className="w-3.5 h-3.5" />
                        Export PNG
                    </button>
                </div>
                <div id="chart-container" className="h-[400px] w-full bg-gray-900/30 rounded-xl p-4 border border-gray-800">
                    <ResponsiveContainer width="100%" height="100%">
                        {chartConfig.type === 'bar' ? (
                            <BarChart {...commonProps}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                <XAxis dataKey={chartConfig.xAxis} stroke="#9ca3af" fontSize={11} angle={-45} textAnchor="end" interval={0} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }} />
                                <Legend verticalAlign="top" height={36} />
                                {chartConfig.yAxes.map((y, i) => (
                                    <Bar key={y} dataKey={y} fill={COLORS[i % COLORS.length]} stackId={chartConfig.stack ? 'a' : undefined} radius={chartConfig.stack ? [0, 0, 0, 0] : [4, 4, 0, 0]} />
                                ))}
                            </BarChart>
                        ) : chartConfig.type === 'line' ? (
                            <LineChart {...commonProps}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                <XAxis dataKey={chartConfig.xAxis} stroke="#9ca3af" fontSize={11} angle={-45} textAnchor="end" interval={0} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }} />
                                <Legend verticalAlign="top" height={36} />
                                {chartConfig.yAxes.map((y, i) => (
                                    <Line key={y} type="monotone" dataKey={y} stroke={COLORS[i % COLORS.length]} strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                                ))}
                            </LineChart>
                        ) : chartConfig.type === 'area' ? (
                            <AreaChart {...commonProps}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                <XAxis dataKey={chartConfig.xAxis} stroke="#9ca3af" fontSize={11} angle={-45} textAnchor="end" interval={0} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }} />
                                <Legend verticalAlign="top" height={36} />
                                {chartConfig.yAxes.map((y, i) => (
                                    <Area key={y} type="monotone" dataKey={y} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.3} stackId={chartConfig.stack ? 'a' : undefined} />
                                ))}
                            </AreaChart>
                        ) : (
                            <PieChart>
                                <Pie
                                    data={chartData}
                                    dataKey={chartConfig.yAxes[0]}
                                    nameKey={chartConfig.xAxis}
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={120}
                                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                                >
                                    {chartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', color: '#fff' }} />
                                <Legend />
                            </PieChart>
                        )}
                    </ResponsiveContainer>
                </div>
            </div>
        )
    }

    return (
        <div className="p-6 space-y-8">
            {!data ? (
                <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-gray-800 rounded-2xl bg-gray-900/50">
                    <div className="p-4 bg-gray-800 rounded-full mb-4">
                        <Upload className="w-8 h-8 text-blue-400" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">Upload your dataset</h3>
                    <p className="text-gray-500 mb-6">CSV, Excel or JSON files supported (Max 50MB)</p>
                    <div className="flex flex-col items-center gap-4">
                        <label className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl cursor-pointer transition-all shadow-lg shadow-blue-900/20">
                            Select File
                            <input type="file" className="hidden" onChange={handleUpload} accept=".csv,.xlsx,.xls,.json" />
                        </label>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <span>Preview rows:</span>
                            <input
                                type="number"
                                value={previewRows}
                                onChange={(e) => setPreviewRows(Number(e.target.value))}
                                className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-center"
                            />
                        </div>
                    </div>
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Header & Controls */}
                    <div className="flex items-center justify-between p-4 bg-gray-800 rounded-xl border border-gray-700">
                        <div className="flex items-center gap-4">
                            <div className="p-2 bg-blue-600/20 rounded-lg">
                                <FileText className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <div className="font-bold text-white">{file?.name}</div>
                                <div className="text-sm text-gray-500">{data.total_rows} total rows • {data.preview.length} rows previewed</div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setData(null)}
                                className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all"
                            >
                                <Trash2 className="w-5 h-5" />
                            </button>
                            <button
                                onClick={handleExport}
                                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-all"
                            >
                                <Download className="w-4 h-4" />
                                Export
                            </button>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="grid grid-cols-3 gap-4">
                        <button
                            onClick={() => setActiveModal('clean')}
                            className={`flex items-center justify-center gap-3 p-4 bg-gray-800 border rounded-xl transition-all group ${activeModal === 'clean' ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-blue-500/50'}`}
                        >
                            <Trash2 className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
                            <span className="font-medium">Clean Data</span>
                        </button>
                        <button
                            onClick={() => setActiveModal('filter')}
                            className={`flex items-center justify-center gap-3 p-4 bg-gray-800 border rounded-xl transition-all group ${activeModal === 'filter' ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-blue-500/50'}`}
                        >
                            <Filter className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
                            <span className="font-medium">Filter</span>
                        </button>
                        <button
                            onClick={() => setActiveModal('summarize')}
                            className={`flex items-center justify-center gap-3 p-4 bg-gray-800 border rounded-xl transition-all group ${activeModal === 'summarize' ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-blue-500/50'}`}
                        >
                            <BarChart2 className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
                            <span className="font-medium">Summarize</span>
                        </button>
                        <button
                            onClick={() => setActiveModal('visualize')}
                            className={`flex items-center justify-center gap-3 p-4 bg-gray-800 border rounded-xl transition-all group ${activeModal === 'visualize' ? 'border-blue-500 bg-blue-500/5' : 'border-gray-700 hover:border-blue-500/50'}`}
                        >
                            <BarChartIcon className="w-5 h-5 text-gray-400 group-hover:text-blue-400" />
                            <span className="font-medium">Visualize</span>
                        </button>
                        <button
                            onClick={handleAutoClean}
                            disabled={loading}
                            className={`flex items-center justify-center gap-3 p-4 bg-gradient-to-r from-purple-600 to-blue-600 border border-purple-500 rounded-xl transition-all group hover:shadow-lg hover:shadow-purple-500/50 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            <Sparkles className="w-5 h-5 text-white" />
                            <span className="font-bold text-white">Auto Clean Data</span>
                        </button>
                        <button
                            onClick={handleExplainDataset}
                            disabled={loading}
                            className={`flex items-center justify-center gap-3 p-4 bg-gradient-to-r from-yellow-600 to-orange-600 border border-yellow-500 rounded-xl transition-all group hover:shadow-lg hover:shadow-yellow-500/50 ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            <Lightbulb className="w-5 h-5 text-white" />
                            <span className="font-bold text-white">Explain Dataset</span>
                        </button>
                    </div>

                    {/* Active Tool Panel */}
                    {activeModal && (
                        <div className="bg-gray-800/50 border border-blue-500/30 rounded-2xl p-6 animate-in fade-in slide-in-from-top-4 duration-300">
                            <div className="flex items-center justify-between mb-6">
                                <h4 className="text-lg font-bold text-white flex items-center gap-2">
                                    {activeModal === 'clean' && <><Trash2 className="w-5 h-5 text-blue-400" /> Cleaning Options</>}
                                    {activeModal === 'filter' && <><Filter className="w-5 h-5 text-blue-400" /> Advanced Filtering</>}
                                    {activeModal === 'summarize' && <><BarChart2 className="w-5 h-5 text-blue-400" /> Data Summary</>}
                                    {activeModal === 'visualize' && <><BarChartIcon className="w-5 h-5 text-blue-400" /> Visualization</>}
                                    {activeModal === 'auto-clean' && <><Sparkles className="w-5 h-5 text-purple-400" /> Auto-Clean Results</>}
                                    {activeModal === 'explain' && <><Lightbulb className="w-5 h-5 text-yellow-400" /> Dataset Explanation</>}
                                </h4>
                                <button onClick={() => setActiveModal(null)} className="text-gray-500 hover:text-white transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            {activeModal === 'clean' && (
                                <div className="grid grid-cols-2 gap-6">
                                    <div className="space-y-4">
                                        {Object.keys(cleanOptions).map(opt => (
                                            <label key={opt} className="flex items-center gap-3 cursor-pointer group">
                                                <div
                                                    onClick={() => setCleanOptions(prev => ({ ...prev, [opt]: !prev[opt] }))}
                                                    className={`w-5 h-5 rounded border flex items-center justify-center transition-all ${cleanOptions[opt] ? 'bg-blue-600 border-blue-600' : 'border-gray-600 group-hover:border-blue-400'}`}
                                                >
                                                    {cleanOptions[opt] && <Check className="w-3 h-3 text-white" />}
                                                </div>
                                                <span className="text-gray-300 capitalize">{opt.replace('_', ' ')}</span>
                                            </label>
                                        ))}
                                    </div>
                                    <div className="flex items-end justify-end">
                                        <button
                                            onClick={() => applyProcessing('clean', cleanOptions)}
                                            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition-all"
                                        >
                                            Apply Cleaning
                                        </button>
                                    </div>
                                </div>
                            )}

                            {activeModal === 'filter' && (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-4 mb-4">
                                        <span className="text-sm text-gray-400">Logic:</span>
                                        <button
                                            onClick={() => setFilterLogic('AND')}
                                            className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${filterLogic === 'AND' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}
                                        >
                                            AND
                                        </button>
                                        <button
                                            onClick={() => setFilterLogic('OR')}
                                            className={`px-3 py-1 rounded-md text-xs font-bold transition-all ${filterLogic === 'OR' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'}`}
                                        >
                                            OR
                                        </button>
                                    </div>
                                    {filterConditions.map((cond, idx) => (
                                        <div key={idx} className="flex items-center gap-3">
                                            <select
                                                value={cond.column}
                                                onChange={(e) => {
                                                    const newConds = [...filterConditions]
                                                    newConds[idx].column = e.target.value
                                                    setFilterConditions(newConds)
                                                }}
                                                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
                                            >
                                                <option value="">Select Column</option>
                                                {data.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                                            </select>
                                            <select
                                                value={cond.operator}
                                                onChange={(e) => {
                                                    const newConds = [...filterConditions]
                                                    newConds[idx].operator = e.target.value
                                                    setFilterConditions(newConds)
                                                }}
                                                className="w-40 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
                                            >
                                                <option value="equals">Equals</option>
                                                <option value="contains">Contains</option>
                                                <option value="greater_than">Greater Than</option>
                                                <option value="less_than">Less Than</option>
                                                <option value="is_null">Is Null</option>
                                            </select>
                                            <input
                                                type="text"
                                                value={cond.value}
                                                onChange={(e) => {
                                                    const newConds = [...filterConditions]
                                                    newConds[idx].value = e.target.value
                                                    setFilterConditions(newConds)
                                                }}
                                                placeholder="Value"
                                                className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
                                            />
                                            <button
                                                onClick={() => setFilterConditions(prev => prev.filter((_, i) => i !== idx))}
                                                className="p-2 text-gray-500 hover:text-red-400 transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                    <div className="flex items-center justify-between pt-4">
                                        <button
                                            onClick={() => setFilterConditions([...filterConditions, { column: '', operator: 'contains', value: '' }])}
                                            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                                        >
                                            <Plus className="w-4 h-4" /> Add Condition
                                        </button>
                                        <button
                                            onClick={() => applyProcessing('filter', { conditions: filterConditions, logic: filterLogic })}
                                            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition-all"
                                        >
                                            Apply Filters
                                        </button>
                                    </div>
                                </div>
                            )}

                            {activeModal === 'summarize' && (
                                <div className="space-y-6">
                                    <div className="grid grid-cols-2 gap-6">
                                        {/* Group By Section */}
                                        <div className="space-y-3">
                                            <label className="text-sm text-gray-400 font-bold">Group By Columns</label>
                                            <p className="text-xs text-gray-600">Select columns to group your data by</p>
                                            <div className="flex flex-wrap gap-2 p-3 bg-gray-900/50 border border-gray-700 rounded-lg min-h-[80px]">
                                                {data.columns.map(col => (
                                                    <button
                                                        key={col.name}
                                                        onClick={() => {
                                                            const isSelected = summaryConfig.group_by.includes(col.name);
                                                            setSummaryConfig(prev => ({
                                                                ...prev,
                                                                group_by: isSelected
                                                                    ? prev.group_by.filter(g => g !== col.name)
                                                                    : [...prev.group_by, col.name]
                                                            }));
                                                        }}
                                                        className={`px-2 py-1 rounded text-xs font-bold transition-all ${summaryConfig.group_by.includes(col.name)
                                                            ? 'bg-purple-600 text-white'
                                                            : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                                                            }`}
                                                    >
                                                        {col.name}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Aggregations Section */}
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <label className="text-sm text-gray-400 font-bold">Aggregations</label>
                                                    <p className="text-xs text-gray-600">Calculate statistics for columns</p>
                                                </div>
                                                <button
                                                    onClick={() => setSummaryConfig(prev => ({
                                                        ...prev,
                                                        aggregations: [...prev.aggregations, { column: data.columns[0]?.name || '', func: 'count' }]
                                                    }))}
                                                    className="flex items-center gap-1 px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded transition-all"
                                                >
                                                    <Plus className="w-3 h-3" />
                                                    Add
                                                </button>
                                            </div>

                                            <div className="space-y-2 max-h-[200px] overflow-y-auto">
                                                {summaryConfig.aggregations.length === 0 ? (
                                                    <div className="p-4 bg-gray-900/30 border border-dashed border-gray-700 rounded text-center text-xs text-gray-600">
                                                        No aggregations added yet
                                                    </div>
                                                ) : (
                                                    summaryConfig.aggregations.map((agg, idx) => (
                                                        <div key={idx} className="flex items-center gap-2">
                                                            <select
                                                                value={agg.column}
                                                                onChange={(e) => {
                                                                    const newAggs = [...summaryConfig.aggregations];
                                                                    newAggs[idx].column = e.target.value;
                                                                    setSummaryConfig(prev => ({ ...prev, aggregations: newAggs }));
                                                                }}
                                                                className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
                                                            >
                                                                {data.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                                                            </select>
                                                            <select
                                                                value={agg.func}
                                                                onChange={(e) => {
                                                                    const newAggs = [...summaryConfig.aggregations];
                                                                    newAggs[idx].func = e.target.value;
                                                                    setSummaryConfig(prev => ({ ...prev, aggregations: newAggs }));
                                                                }}
                                                                className="w-28 bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-200"
                                                            >
                                                                <option value="count">Count</option>
                                                                <option value="sum">Sum</option>
                                                                <option value="mean">Average</option>
                                                                <option value="min">Min</option>
                                                                <option value="max">Max</option>
                                                            </select>
                                                            <button
                                                                onClick={() => setSummaryConfig(prev => ({
                                                                    ...prev,
                                                                    aggregations: prev.aggregations.filter((_, i) => i !== idx)
                                                                }))}
                                                                className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                                                            >
                                                                <X className="w-3.5 h-3.5" />
                                                            </button>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Example Preview */}
                                    <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-xl">
                                        <div className="flex items-start gap-3">
                                            <div className="p-2 bg-blue-600/20 rounded-lg">
                                                <BarChart2 className="w-4 h-4 text-blue-400" />
                                            </div>
                                            <div className="flex-1">
                                                <h4 className="text-sm font-bold text-blue-400 mb-1">What does Summarize do?</h4>
                                                <p className="text-xs text-gray-400 mb-2">
                                                    Summarize groups your data and calculates statistics. For example:
                                                </p>
                                                <ul className="text-xs text-gray-500 space-y-1">
                                                    <li>• Group by "Country" → Count how many buildings per country</li>
                                                    <li>• Group by "City" + Aggregate "Height" (Average) → Average building height per city</li>
                                                    <li>• No grouping + Aggregate "Price" (Sum) → Total sum of all prices</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex justify-end">
                                        <button
                                            onClick={() => applyProcessing('summarize', summaryConfig)}
                                            disabled={summaryConfig.aggregations.length === 0}
                                            className={`px-6 py-2 font-bold rounded-lg transition-all ${summaryConfig.aggregations.length === 0
                                                ? 'bg-gray-800 text-gray-600 cursor-not-allowed'
                                                : 'bg-blue-600 hover:bg-blue-500 text-white'
                                                }`}
                                        >
                                            Apply Summary
                                        </button>
                                    </div>
                                </div>
                            )}

                            {activeModal === 'visualize' && (
                                <div className="space-y-8">
                                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-xs text-gray-500 uppercase font-bold">Chart Type</label>
                                            <select
                                                value={chartConfig.type}
                                                onChange={(e) => setChartConfig(prev => ({ ...prev, type: e.target.value, autoSuggest: false }))}
                                                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
                                            >
                                                <option value="bar">Bar Chart</option>
                                                <option value="line">Line Chart</option>
                                                <option value="area">Area Chart</option>
                                                <option value="pie">Pie Chart</option>
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs text-gray-500 uppercase font-bold">X-Axis (Label)</label>
                                            <select
                                                value={chartConfig.xAxis}
                                                onChange={(e) => setChartConfig(prev => ({ ...prev, xAxis: e.target.value }))}
                                                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
                                            >
                                                {data.columns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-2 col-span-2">
                                            <label className="text-xs text-gray-500 uppercase font-bold">
                                                Y-Axes (Values)
                                                <span className="text-[10px] text-blue-400 ml-2 normal-case font-normal">Click to select/deselect</span>
                                            </label>
                                            <div className="flex flex-wrap gap-2 p-2 bg-gray-900 border border-gray-700 rounded-lg min-h-[42px]">
                                                {data.columns.map(col => {
                                                    const isNumeric = col.type === 'numeric';
                                                    const isSelected = chartConfig.yAxes.includes(col.name);
                                                    return (
                                                        <button
                                                            key={col.name}
                                                            onClick={() => {
                                                                setChartConfig(prev => ({
                                                                    ...prev,
                                                                    yAxes: isSelected
                                                                        ? prev.yAxes.filter(y => y !== col.name)
                                                                        : [...prev.yAxes, col.name],
                                                                    autoSuggest: false
                                                                }));
                                                            }}
                                                            className={`px-2 py-1 rounded text-[10px] font-bold transition-all ${isSelected
                                                                ? 'bg-blue-600 text-white'
                                                                : isNumeric
                                                                    ? 'bg-green-900/30 text-green-400 hover:bg-green-900/50'
                                                                    : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                                                                }`}
                                                        >
                                                            {col.name} {!isNumeric && '(count)'}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                            <p className="text-[10px] text-gray-500 italic">
                                                💡 Numeric columns shown in green. Non-numeric columns will be counted automatically.
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-6 text-sm">
                                        <label className="flex items-center gap-2 cursor-pointer group">
                                            <div
                                                onClick={() => setChartConfig(prev => ({ ...prev, stack: !prev.stack }))}
                                                className={`w-4 h-4 rounded border flex items-center justify-center transition-all ${chartConfig.stack ? 'bg-blue-600 border-blue-600' : 'border-gray-600 group-hover:border-blue-400'}`}
                                            >
                                                {chartConfig.stack && <Check className="w-2.5 h-2.5 text-white" />}
                                            </div>
                                            <span className="text-gray-400">Stack Datasets</span>
                                        </label>
                                        {chartConfig.autoSuggest && (
                                            <span className="text-[10px] bg-blue-600/20 text-blue-400 px-2 py-0.5 rounded-full font-bold animate-pulse">
                                                Auto-suggested based on data
                                            </span>
                                        )}
                                    </div>

                                    {renderChart()}
                                </div>
                            )}

                            {activeModal === 'auto-clean' && cleaningReport && (
                                <div className="space-y-6">
                                    {/* Summary Stats */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="p-4 bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-xl">
                                            <div className="text-sm text-gray-400 mb-1">Before Cleaning</div>
                                            <div className="text-2xl font-bold text-white">{cleaningReport.original_rows.toLocaleString()} rows</div>
                                            <div className="text-xs text-gray-500">{cleaningReport.original_columns} columns</div>
                                        </div>
                                        <div className="p-4 bg-gradient-to-br from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-xl">
                                            <div className="text-sm text-gray-400 mb-1">After Cleaning</div>
                                            <div className="text-2xl font-bold text-green-400">{cleaningReport.final_rows.toLocaleString()} rows</div>
                                            <div className="text-xs text-gray-500">{cleaningReport.final_columns} columns</div>
                                        </div>
                                    </div>

                                    {/* Cleaning Summary */}
                                    <div className="p-4 bg-gray-900/50 border border-gray-700 rounded-xl">
                                        <h5 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                                            <Check className="w-4 h-4 text-green-400" />
                                            Changes Made
                                        </h5>
                                        {cleaningReport.summary.length === 0 ? (
                                            <p className="text-sm text-gray-400 italic">No changes needed - dataset is already clean!</p>
                                        ) : (
                                            <ul className="space-y-2">
                                                {cleaningReport.summary.map((item, idx) => (
                                                    <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                                                        <span className="text-green-400 mt-0.5">✓</span>
                                                        <span>{item}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>

                                    {/* Download Options */}
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={handleExport}
                                            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition-all"
                                        >
                                            <Download className="w-4 h-4" />
                                            Download Cleaned CSV
                                        </button>
                                        <button
                                            onClick={() => downloadCleaningReport('json')}
                                            className="flex items-center gap-2 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-all"
                                        >
                                            <Download className="w-4 h-4" />
                                            Report (JSON)
                                        </button>
                                        <button
                                            onClick={() => downloadCleaningReport('txt')}
                                            className="flex items-center gap-2 px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-all"
                                        >
                                            <Download className="w-4 h-4" />
                                            Report (TXT)
                                        </button>
                                    </div>
                                </div>
                            )}

                            {activeModal === 'explain' && datasetExplanation && (
                                <div className="space-y-6">
                                    {/* Overview */}
                                    <div className="grid grid-cols-4 gap-4">
                                        <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                                            <div className="text-xs text-gray-400 mb-1">Total Rows</div>
                                            <div className="text-xl font-bold text-blue-400">{datasetExplanation.overview.total_rows.toLocaleString()}</div>
                                        </div>
                                        <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
                                            <div className="text-xs text-gray-400 mb-1">Total Columns</div>
                                            <div className="text-xl font-bold text-purple-400">{datasetExplanation.overview.total_columns}</div>
                                        </div>
                                        <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
                                            <div className="text-xs text-gray-400 mb-1">Completeness</div>
                                            <div className="text-xl font-bold text-green-400">{datasetExplanation.overview.completeness_percentage}%</div>
                                        </div>
                                        <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                                            <div className="text-xs text-gray-400 mb-1">Dataset Type</div>
                                            <div className="text-sm font-bold text-yellow-400">{datasetExplanation.inferred_purpose}</div>
                                        </div>
                                    </div>

                                    {/* Explanation Text */}
                                    <div className="p-6 bg-gradient-to-br from-yellow-500/5 to-orange-500/5 border border-yellow-500/20 rounded-xl">
                                        <div className="flex items-start gap-3 mb-4">
                                            <div className="p-2 bg-yellow-600/20 rounded-lg">
                                                <Lightbulb className="w-5 h-5 text-yellow-400" />
                                            </div>
                                            <div className="flex-1">
                                                <h5 className="text-lg font-bold text-white mb-2">Dataset Insights</h5>
                                                <div className="prose prose-invert prose-sm max-w-none">
                                                    {datasetExplanation.explanation.split('\n').map((line, idx) => {
                                                        if (line.startsWith('###')) {
                                                            return <h6 key={idx} className="text-base font-bold text-blue-400 mt-4 mb-2">{line.replace('###', '').trim()}</h6>
                                                        } else if (line.startsWith('-')) {
                                                            return <p key={idx} className="text-sm text-gray-300 ml-4">{line}</p>
                                                        } else if (line.match(/^\d+\./)) {
                                                            return <p key={idx} className="text-sm text-gray-300 ml-4">{line}</p>
                                                        } else if (line.trim()) {
                                                            // Replace **bold** with actual bold
                                                            const parts = line.split(/\*\*(.*?)\*\*/g)
                                                            return (
                                                                <p key={idx} className="text-sm text-gray-300 mb-2">
                                                                    {parts.map((part, i) =>
                                                                        i % 2 === 1 ? <strong key={i} className="text-white font-bold">{part}</strong> : part
                                                                    )}
                                                                </p>
                                                            )
                                                        }
                                                        return null
                                                    })}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Column Insights Table */}
                                    <div className="max-h-96 overflow-y-auto rounded-xl border border-gray-800 bg-gray-900/30">
                                        <table className="w-full text-left border-collapse">
                                            <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider sticky top-0">
                                                <tr>
                                                    <th className="px-4 py-3 font-bold border-b border-gray-700">Column</th>
                                                    <th className="px-4 py-3 font-bold border-b border-gray-700">Type</th>
                                                    <th className="px-4 py-3 font-bold border-b border-gray-700">Key Stats</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-800">
                                                {Object.entries(datasetExplanation.column_insights.columns).map(([colName, colInfo]) => {
                                                    const numericStats = datasetExplanation.column_insights.numeric[colName]
                                                    const categoricalStats = datasetExplanation.column_insights.categorical[colName]

                                                    return (
                                                        <tr key={colName} className="hover:bg-gray-800/30 transition-colors">
                                                            <td className="px-4 py-3 text-sm font-medium text-white">{colName}</td>
                                                            <td className="px-4 py-3">
                                                                <span className={`text-xs px-2 py-1 rounded ${colInfo.type === 'numeric'
                                                                        ? 'bg-green-500/20 text-green-400'
                                                                        : 'bg-blue-500/20 text-blue-400'
                                                                    }`}>
                                                                    {colInfo.type}
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-3 text-xs text-gray-400">
                                                                {numericStats && (
                                                                    <span>Min: {numericStats.min.toFixed(2)} | Max: {numericStats.max.toFixed(2)} | Avg: {numericStats.mean.toFixed(2)}</span>
                                                                )}
                                                                {categoricalStats && (
                                                                    <span>Unique: {categoricalStats.unique_count} | Most common: {categoricalStats.most_common}</span>
                                                                )}
                                                            </td>
                                                        </tr>
                                                    )
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Table View */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-white">Data Preview</h3>
                            <div className="flex items-center gap-4 text-sm text-gray-500">
                                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-blue-500"></div> String</span>
                                <span className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-green-500"></div> Numeric</span>
                            </div>
                        </div>
                        <div className="overflow-x-auto rounded-xl border border-gray-800 bg-gray-900/30">
                            <table className="w-full text-left border-collapse">
                                <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider">
                                    <tr>
                                        {data.columns.map(col => (
                                            <th key={col.name} className="px-4 py-4 font-bold border-b border-gray-700">
                                                <div className="flex items-center gap-2">
                                                    <span className={col.type === 'numeric' ? 'text-green-400' : 'text-blue-400'}>
                                                        {col.name}
                                                    </span>
                                                    <span className="text-[10px] bg-gray-700 px-1.5 py-0.5 rounded opacity-50">{col.type}</span>
                                                </div>
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-800">
                                    {data.preview.map((row, i) => (
                                        <tr key={i} className="hover:bg-gray-800/30 transition-colors group">
                                            {data.columns.map(col => (
                                                <td key={col.name} className="px-4 py-3 text-sm text-gray-300 truncate max-w-[200px]">
                                                    {String(row[col.name] ?? '')}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
