import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Activity, DollarSign, Zap, TrendingUp, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, analyticsRes, historyRes] = await Promise.all([
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/analytics`),
        fetch(`${API_URL}/history?limit=50`)
      ]);

      const statsData = await statsRes.json();
      const analyticsData = await analyticsRes.json();
      const historyData = await historyRes.json();

      setStats(statsData);
      setAnalytics(analyticsData);
      setHistory(historyData.requests || []);
    } catch (err) {
      setError('Failed to fetch data. Make sure backend is running on port 8000.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-800 mb-2 text-center">Connection Error</h2>
          <p className="text-gray-600 text-center mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Calculate metrics
  const cacheHitRate = stats?.router?.cache_hit_rate || 0;
  const totalCost = analytics?.total_cost || 0;
  const totalSavings = analytics?.total_savings || 0;
  const totalRequests = analytics?.total_requests || 0;

  // Prepare chart data
  const modelUsageData = Object.entries(analytics?.model_usage || {}).map(([name, value]) => ({
    name: name.replace('gemini-', ''),
    value
  }));

  const cacheData = [
    { name: 'Exact Hits', value: analytics?.cache_stats?.exact_hits || 0 },
    { name: 'Semantic Hits', value: analytics?.cache_stats?.semantic_hits || 0 },
    { name: 'Misses', value: analytics?.cache_stats?.misses || 0 }
  ];

  const recentQueries = history.slice(0, 10);

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">🔥 LLM Cost Firewall</h1>
              <p className="text-sm text-gray-500 mt-1">Real-time cost optimization dashboard</p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Requests */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Requests</p>
                <p className="text-3xl font-bold text-gray-900">{totalRequests}</p>
              </div>
              <div className="bg-blue-100 p-3 rounded-full">
                <Activity className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </div>

          {/* Total Cost */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Cost</p>
                <p className="text-3xl font-bold text-gray-900">${totalCost.toFixed(4)}</p>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>

          {/* Cache Hit Rate */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Cache Hit Rate</p>
                <p className="text-3xl font-bold text-gray-900">{cacheHitRate.toFixed(1)}%</p>
              </div>
              <div className="bg-purple-100 p-3 rounded-full">
                <Zap className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </div>

          {/* Total Savings */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Savings</p>
                <p className="text-3xl font-bold text-green-600">${totalSavings.toFixed(4)}</p>
              </div>
              <div className="bg-green-100 p-3 rounded-full">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Model Usage */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Usage Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={modelUsageData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {modelUsageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Cache Performance */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Cache Performance</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={cacheData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent Queries */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Recent Queries</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Query</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cached</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latency</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {recentQueries.map((req, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                      {req.query || 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        {req.model?.replace('gemini-', '') || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      ${parseFloat(req.cost || 0).toFixed(4)}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {req.cached ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {req.latency_ms ? `${req.latency_ms}ms` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Last updated: {new Date().toLocaleTimeString()} • Auto-refresh every 10s</p>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;