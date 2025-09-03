import { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import {
  FileText,
  Download,
  Filter,
  Calendar,
  Users,
  TrendingUp,
  FileSpreadsheet,
  FilePdf,
  RefreshCw,
  Eye,
} from 'lucide-react';
import { format } from 'date-fns';
import api from '@/services/api';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [groups, setGroups] = useState([]);
  const [filters, setFilters] = useState({
    startDate: new Date(new Date().setDate(new Date().getDate() - 30)),
    endDate: new Date(),
    groupId: 'all',
    reportType: 'all',
  });
  const [reportStats, setReportStats] = useState({
    totalReports: 0,
    thisMonth: 0,
    averageAttendance: 0,
    totalStudents: 0,
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  useEffect(() => {
    fetchReports();
  }, [filters]);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      // Fetch groups
      const groupsResponse = await api.get('/groups');
      setGroups(groupsResponse.data);

      // Fetch report statistics
      const statsResponse = await api.get('/reports/statistics');
      setReportStats(statsResponse.data);
    } catch (error) {
      console.error('Error fetching initial data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = {
        startDate: filters.startDate.toISOString(),
        endDate: filters.endDate.toISOString(),
        groupId: filters.groupId !== 'all' ? filters.groupId : undefined,
        type: filters.reportType !== 'all' ? filters.reportType : undefined,
      };

      const response = await api.get('/reports', { params });
      setReports(response.data);
    } catch (error) {
      console.error('Error fetching reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async (type) => {
    setGenerating(true);
    try {
      const params = {
        type,
        startDate: filters.startDate.toISOString(),
        endDate: filters.endDate.toISOString(),
        groupId: filters.groupId !== 'all' ? filters.groupId : undefined,
      };

      const response = await api.post('/reports/generate', params);
      
      // Refresh reports list
      await fetchReports();
      
      // Show success message
      alert(`Report generated successfully: ${response.data.name}`);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const downloadReport = async (reportId, format) => {
    try {
      const response = await api.get(`/reports/${reportId}/download`, {
        params: { format },
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report-${reportId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Error downloading report:', error);
      alert('Failed to download report');
    }
  };

  const previewReport = async (reportId) => {
    try {
      const response = await api.get(`/reports/${reportId}/preview`);
      // Open preview in new window
      const newWindow = window.open('', '_blank');
      newWindow.document.write(response.data);
    } catch (error) {
      console.error('Error previewing report:', error);
    }
  };

  const getReportTypeIcon = (type) => {
    switch (type) {
      case 'attendance':
        return <Users className="h-4 w-4" />;
      case 'performance':
        return <TrendingUp className="h-4 w-4" />;
      case 'summary':
        return <FileText className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getReportTypeColor = (type) => {
    switch (type) {
      case 'attendance':
        return 'bg-blue-100 text-blue-800';
      case 'performance':
        return 'bg-green-100 text-green-800';
      case 'summary':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-600">Generate and download attendance reports</p>
        </div>
        <button
          onClick={() => fetchReports()}
          className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Reports</p>
              <p className="text-2xl font-bold text-gray-900">
                {reportStats.totalReports}
              </p>
            </div>
            <FileText className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">This Month</p>
              <p className="text-2xl font-bold text-gray-900">
                {reportStats.thisMonth}
              </p>
            </div>
            <Calendar className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg. Attendance</p>
              <p className="text-2xl font-bold text-gray-900">
                {reportStats.averageAttendance}%
              </p>
            </div>
            <TrendingUp className="h-8 w-8 text-purple-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Students</p>
              <p className="text-2xl font-bold text-gray-900">
                {reportStats.totalStudents}
              </p>
            </div>
            <Users className="h-8 w-8 text-yellow-500" />
          </div>
        </div>
      </div>

      {/* Generate Report Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate New Report</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => generateReport('attendance')}
            disabled={generating}
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors disabled:opacity-50"
          >
            <Users className="h-8 w-8 text-blue-500 mb-2" />
            <span className="text-sm font-medium text-gray-900">Attendance Report</span>
            <span className="text-xs text-gray-500 mt-1">Daily attendance records</span>
          </button>

          <button
            onClick={() => generateReport('performance')}
            disabled={generating}
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-500 hover:bg-green-50 transition-colors disabled:opacity-50"
          >
            <TrendingUp className="h-8 w-8 text-green-500 mb-2" />
            <span className="text-sm font-medium text-gray-900">Performance Report</span>
            <span className="text-xs text-gray-500 mt-1">Student performance analysis</span>
          </button>

          <button
            onClick={() => generateReport('summary')}
            disabled={generating}
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-colors disabled:opacity-50"
          >
            <FileText className="h-8 w-8 text-purple-500 mb-2" />
            <span className="text-sm font-medium text-gray-900">Summary Report</span>
            <span className="text-xs text-gray-500 mt-1">Comprehensive overview</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Filter className="h-5 w-5 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>

          <div>
            <DatePicker
              selected={filters.startDate}
              onChange={(date) => setFilters({ ...filters, startDate: date })}
              dateFormat="MMM d, yyyy"
              className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholderText="Start Date"
            />
          </div>

          <div>
            <DatePicker
              selected={filters.endDate}
              onChange={(date) => setFilters({ ...filters, endDate: date })}
              dateFormat="MMM d, yyyy"
              minDate={filters.startDate}
              className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
              placeholderText="End Date"
            />
          </div>

          <select
            value={filters.groupId}
            onChange={(e) => setFilters({ ...filters, groupId: e.target.value })}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Groups</option>
            {groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>

          <select
            value={filters.reportType}
            onChange={(e) => setFilters({ ...filters, reportType: e.target.value })}
            className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            <option value="attendance">Attendance</option>
            <option value="performance">Performance</option>
            <option value="summary">Summary</option>
          </select>
        </div>
      </div>

      {/* Reports Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Report
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date Range
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Group
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Generated
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : reports.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-gray-500">
                    No reports found
                  </td>
                </tr>
              ) : (
                reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <FileText className="h-5 w-5 text-gray-400 mr-3" />
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {report.name}
                          </div>
                          <div className="text-sm text-gray-500">
                            {report.description}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getReportTypeColor(
                          report.type
                        )}`}
                      >
                        {getReportTypeIcon(report.type)}
                        <span className="ml-1 capitalize">{report.type}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {format(new Date(report.startDate), 'MMM d')} -{' '}
                      {format(new Date(report.endDate), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {report.groupName || 'All Groups'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(report.createdAt), 'MMM d, yyyy h:mm a')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button
                          onClick={() => previewReport(report.id)}
                          className="text-blue-600 hover:text-blue-900"
                          title="Preview"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => downloadReport(report.id, 'csv')}
                          className="text-green-600 hover:text-green-900"
                          title="Download CSV"
                        >
                          <FileSpreadsheet className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => downloadReport(report.id, 'pdf')}
                          className="text-red-600 hover:text-red-900"
                          title="Download PDF"
                        >
                          <FilePdf className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Reports;
