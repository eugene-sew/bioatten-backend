import { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import {
  Calendar,
  Clock,
  Plus,
  Edit2,
  Trash2,
  X,
  Users,
  MapPin,
  RepeatIcon,
} from 'lucide-react';
import { format } from 'date-fns';
import api from '@/services/api';
import useScheduleStore from '@/store/scheduleStore';

const Schedules = () => {
  const { schedules, fetchSchedules, addSchedule, updateSchedule, deleteSchedule } = useScheduleStore();
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [groups, setGroups] = useState([]);
  const [formData, setFormData] = useState({
    title: '',
    groupId: '',
    startTime: new Date(),
    endTime: new Date(),
    location: '',
    instructor: '',
    recurrence: 'none',
    recurrenceEnd: null,
    description: '',
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      await fetchSchedules();
      const groupsResponse = await api.get('/groups');
      setGroups(groupsResponse.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = (schedule = null) => {
    if (schedule) {
      setEditingSchedule(schedule);
      setFormData({
        title: schedule.title,
        groupId: schedule.groupId,
        startTime: new Date(schedule.startTime),
        endTime: new Date(schedule.endTime),
        location: schedule.location || '',
        instructor: schedule.instructor || '',
        recurrence: schedule.recurrence || 'none',
        recurrenceEnd: schedule.recurrenceEnd ? new Date(schedule.recurrenceEnd) : null,
        description: schedule.description || '',
      });
    } else {
      setEditingSchedule(null);
      const now = new Date();
      const later = new Date(now.getTime() + 60 * 60 * 1000);
      setFormData({
        title: '',
        groupId: '',
        startTime: now,
        endTime: later,
        location: '',
        instructor: '',
        recurrence: 'none',
        recurrenceEnd: null,
        description: '',
      });
    }
    setErrors({});
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingSchedule(null);
    setErrors({});
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    if (!formData.groupId) {
      newErrors.groupId = 'Group is required';
    }
    if (formData.startTime >= formData.endTime) {
      newErrors.time = 'End time must be after start time';
    }
    if (formData.recurrence !== 'none' && !formData.recurrenceEnd) {
      newErrors.recurrenceEnd = 'Recurrence end date is required';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      const payload = {
        ...formData,
        startTime: formData.startTime.toISOString(),
        endTime: formData.endTime.toISOString(),
        recurrenceEnd: formData.recurrenceEnd ? formData.recurrenceEnd.toISOString() : null,
      };

      if (editingSchedule) {
        await updateSchedule(editingSchedule.id, payload);
      } else {
        await addSchedule(payload);
      }
      handleCloseModal();
    } catch (error) {
      console.error('Error saving schedule:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this schedule?')) {
      try {
        await deleteSchedule(id);
      } catch (error) {
        console.error('Error deleting schedule:', error);
      }
    }
  };

  const getRecurrenceLabel = (recurrence) => {
    const labels = {
      none: 'No repeat',
      daily: 'Daily',
      weekly: 'Weekly',
      monthly: 'Monthly',
    };
    return labels[recurrence] || 'No repeat';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schedules</h1>
          <p className="text-gray-600">Manage class schedules and sessions</p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Schedule
        </button>
      </div>

      {/* Calendar View */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Upcoming Sessions</h2>
        </div>
        <div className="space-y-4">
          {schedules.map((schedule) => (
            <div
              key={schedule.id}
              className="border rounded-lg p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center mb-2">
                    <Calendar className="h-5 w-5 text-gray-400 mr-2" />
                    <h3 className="text-lg font-medium text-gray-900">
                      {schedule.title}
                    </h3>
                    {schedule.recurrence !== 'none' && (
                      <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                        <RepeatIcon className="inline h-3 w-3 mr-1" />
                        {getRecurrenceLabel(schedule.recurrence)}
                      </span>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                    <div className="flex items-center text-gray-600">
                      <Clock className="h-4 w-4 mr-2" />
                      {format(new Date(schedule.startTime), 'MMM dd, yyyy')} at{' '}
                      {format(new Date(schedule.startTime), 'h:mm a')} -{' '}
                      {format(new Date(schedule.endTime), 'h:mm a')}
                    </div>
                    <div className="flex items-center text-gray-600">
                      <Users className="h-4 w-4 mr-2" />
                      {groups.find(g => g.id === schedule.groupId)?.name || 'Unknown Group'}
                    </div>
                    {schedule.location && (
                      <div className="flex items-center text-gray-600">
                        <MapPin className="h-4 w-4 mr-2" />
                        {schedule.location}
                      </div>
                    )}
                    {schedule.instructor && (
                      <div className="flex items-center text-gray-600">
                        <Users className="h-4 w-4 mr-2" />
                        {schedule.instructor}
                      </div>
                    )}
                  </div>

                  {schedule.description && (
                    <p className="mt-2 text-sm text-gray-500">{schedule.description}</p>
                  )}
                </div>

                <div className="flex space-x-2 ml-4">
                  <button
                    onClick={() => handleOpenModal(schedule)}
                    className="p-2 text-yellow-600 hover:bg-yellow-50 rounded"
                  >
                    <Edit2 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(schedule.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {schedules.length === 0 && (
          <div className="text-center py-12">
            <Calendar className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-semibold text-gray-900">No schedules</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new schedule.
            </p>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                {editingSchedule ? 'Edit Schedule' : 'Add New Schedule'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Title *
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    className={`mt-1 block w-full rounded-md shadow-sm ${
                      errors.title
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                    }`}
                  />
                  {errors.title && (
                    <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Group *
                  </label>
                  <select
                    value={formData.groupId}
                    onChange={(e) => setFormData({ ...formData, groupId: e.target.value })}
                    className={`mt-1 block w-full rounded-md shadow-sm ${
                      errors.groupId
                        ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                        : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
                    }`}
                  >
                    <option value="">Select a group</option>
                    {groups.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.name}
                      </option>
                    ))}
                  </select>
                  {errors.groupId && (
                    <p className="mt-1 text-sm text-red-600">{errors.groupId}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Start Time *
                  </label>
                  <DatePicker
                    selected={formData.startTime}
                    onChange={(date) => setFormData({ ...formData, startTime: date })}
                    showTimeSelect
                    dateFormat="MMM d, yyyy h:mm aa"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    End Time *
                  </label>
                  <DatePicker
                    selected={formData.endTime}
                    onChange={(date) => setFormData({ ...formData, endTime: date })}
                    showTimeSelect
                    dateFormat="MMM d, yyyy h:mm aa"
                    minDate={formData.startTime}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                  {errors.time && (
                    <p className="mt-1 text-sm text-red-600">{errors.time}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Location
                  </label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="Room 101, Building A"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Instructor
                  </label>
                  <input
                    type="text"
                    value={formData.instructor}
                    onChange={(e) => setFormData({ ...formData, instructor: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Recurrence
                  </label>
                  <select
                    value={formData.recurrence}
                    onChange={(e) => setFormData({ ...formData, recurrence: e.target.value })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                  >
                    <option value="none">No repeat</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                {formData.recurrence !== 'none' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Repeat Until *
                    </label>
                    <DatePicker
                      selected={formData.recurrenceEnd}
                      onChange={(date) => setFormData({ ...formData, recurrenceEnd: date })}
                      dateFormat="MMM d, yyyy"
                      minDate={formData.startTime}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                    {errors.recurrenceEnd && (
                      <p className="mt-1 text-sm text-red-600">{errors.recurrenceEnd}</p>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  {editingSchedule ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Schedules;
