import { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import {
  Monitor,
  Users,
  User,
  UserCheck,
  UserX,
  Clock,
  Activity,
  Wifi,
  WifiOff,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { format } from 'date-fns';
import api from '@/services/api';

const LiveAttendance = () => {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [activeSession, setActiveSession] = useState(null);
  const [attendanceLog, setAttendanceLog] = useState([]);
  const [statistics, setStatistics] = useState({
    totalExpected: 0,
    present: 0,
    absent: 0,
    late: 0,
  });
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('all');
  const logEndRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    const socketUrl = process.env.REACT_APP_WS_URL || 'http://localhost:8000';
    const newSocket = io(socketUrl, {
      transports: ['websocket'],
      auth: {
        token: localStorage.getItem('auth-storage')?.accessToken,
      },
    });

    newSocket.on('connect', () => {
      console.log('Connected to attendance server');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from attendance server');
      setConnected(false);
    });

    newSocket.on('attendance_update', (data) => {
      handleAttendanceUpdate(data);
    });

    newSocket.on('session_started', (data) => {
      setActiveSession(data);
    });

    newSocket.on('session_ended', () => {
      setActiveSession(null);
    });

    setSocket(newSocket);

    // Fetch initial data
    fetchInitialData();

    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, []);

  useEffect(() => {
    // Auto-scroll to latest log entry
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [attendanceLog]);

  const fetchInitialData = async () => {
    try {
      // Fetch groups
      const groupsResponse = await api.get('/groups');
      setGroups(groupsResponse.data);

      // Fetch current session if any
      const sessionResponse = await api.get('/attendance/current-session');
      if (sessionResponse.data) {
        setActiveSession(sessionResponse.data);
      }

      // Fetch today's attendance log
      const logResponse = await api.get('/attendance/today-log');
      setAttendanceLog(logResponse.data);

      // Calculate statistics
      updateStatistics(logResponse.data);
    } catch (error) {
      console.error('Error fetching initial data:', error);
    }
  };

  const handleAttendanceUpdate = (data) => {
    const newEntry = {
      id: Date.now(),
      studentName: data.studentName,
      studentId: data.studentId,
      groupName: data.groupName,
      status: data.status,
      time: new Date(),
      photo: data.photo,
      confidence: data.confidence,
    };

    setAttendanceLog((prev) => [newEntry, ...prev]);
    updateStatistics([newEntry, ...attendanceLog]);
  };

  const updateStatistics = (logs) => {
    const stats = logs.reduce(
      (acc, log) => {
        if (log.status === 'present') acc.present++;
        else if (log.status === 'absent') acc.absent++;
        else if (log.status === 'late') acc.late++;
        return acc;
      },
      { totalExpected: 0, present: 0, absent: 0, late: 0 }
    );

    // Get total expected from active session
    if (activeSession) {
      stats.totalExpected = activeSession.expectedStudents || 0;
    }

    setStatistics(stats);
  };

  const startSession = async () => {
    try {
      const response = await api.post('/attendance/start-session', {
        groupId: selectedGroup !== 'all' ? selectedGroup : null,
      });
      setActiveSession(response.data);
    } catch (error) {
      console.error('Error starting session:', error);
    }
  };

  const endSession = async () => {
    if (!activeSession) return;

    try {
      await api.post('/attendance/end-session', {
        sessionId: activeSession.id,
      });
      setActiveSession(null);
    } catch (error) {
      console.error('Error ending session:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'present':
        return 'text-green-600 bg-green-50';
      case 'late':
        return 'text-yellow-600 bg-yellow-50';
      case 'absent':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'present':
        return <CheckCircle className="h-4 w-4" />;
      case 'late':
        return <Clock className="h-4 w-4" />;
      case 'absent':
        return <UserX className="h-4 w-4" />;
      default:
        return <AlertCircle className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live Attendance Monitor</h1>
          <p className="text-gray-600">Real-time attendance tracking</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            {connected ? (
              <>
                <Wifi className="h-5 w-5 text-green-500 mr-2" />
                <span className="text-sm text-green-600">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-5 w-5 text-red-500 mr-2" />
                <span className="text-sm text-red-600">Disconnected</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Session Control */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Session Control</h2>
          {activeSession && (
            <span className="flex items-center text-sm text-green-600">
              <Activity className="h-4 w-4 mr-1 animate-pulse" />
              Session Active
            </span>
          )}
        </div>

        {!activeSession ? (
          <div className="flex items-center space-x-4">
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Groups</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
            <button
              onClick={startSession}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              Start Session
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Session ID: {activeSession.id}</p>
                  <p className="text-sm text-gray-600">
                    Group: {activeSession.groupName || 'All Groups'}
                  </p>
                  <p className="text-sm text-gray-600">
                    Started: {format(new Date(activeSession.startTime), 'h:mm a')}
                  </p>
                </div>
                <button
                  onClick={endSession}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                >
                  End Session
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Expected</p>
              <p className="text-2xl font-bold text-gray-900">
                {statistics.totalExpected}
              </p>
            </div>
            <Users className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Present</p>
              <p className="text-2xl font-bold text-green-600">
                {statistics.present}
              </p>
            </div>
            <UserCheck className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Late</p>
              <p className="text-2xl font-bold text-yellow-600">
                {statistics.late}
              </p>
            </div>
            <Clock className="h-8 w-8 text-yellow-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Absent</p>
              <p className="text-2xl font-bold text-red-600">
                {statistics.absent}
              </p>
            </div>
            <UserX className="h-8 w-8 text-red-500" />
          </div>
        </div>
      </div>

      {/* Live Feed */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Live Attendance Feed</h2>
        </div>
        <div className="p-6">
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {attendanceLog.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Monitor className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                <p>No attendance records yet</p>
                <p className="text-sm">Start a session to begin tracking</p>
              </div>
            ) : (
              attendanceLog.map((log) => (
                <div
                  key={log.id}
                  className="flex items-center space-x-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  {log.photo ? (
                    <img
                      src={log.photo}
                      alt={log.studentName}
                      className="h-10 w-10 rounded-full object-cover"
                    />
                  ) : (
                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <User className="h-6 w-6 text-gray-600" />
                    </div>
                  )}
                  
                  <div className="flex-1">
                    <div className="flex items-center">
                      <p className="font-medium text-gray-900">{log.studentName}</p>
                      <span className="ml-2 text-sm text-gray-500">
                        ID: {log.studentId}
                      </span>
                      {log.confidence && (
                        <span className="ml-2 text-xs text-gray-400">
                          {(log.confidence * 100).toFixed(1)}% match
                        </span>
                      )}
                    </div>
                    <div className="flex items-center text-sm text-gray-500">
                      <span>{log.groupName}</span>
                      <span className="mx-2">•</span>
                      <span>{format(new Date(log.time), 'h:mm:ss a')}</span>
                    </div>
                  </div>

                  <div
                    className={`flex items-center px-3 py-1 rounded-full ${getStatusColor(
                      log.status
                    )}`}
                  >
                    {getStatusIcon(log.status)}
                    <span className="ml-1 text-sm font-medium capitalize">
                      {log.status}
                    </span>
                  </div>
                </div>
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveAttendance;
