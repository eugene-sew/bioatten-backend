import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import Webcam from 'react-webcam';
import {
  Camera,
  User,
  Mail,
  Phone,
  Users,
  Calendar,
  ChevronRight,
  ChevronLeft,
  Check,
  X,
  RotateCcw,
} from 'lucide-react';
import api from '@/services/api';
import useStudentStore from '@/store/studentStore';

const EnrollStudent = () => {
  const navigate = useNavigate();
  const { addStudent } = useStudentStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [capturedImage, setCapturedImage] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [groups, setGroups] = useState([]);
  const webcamRef = useRef(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
  } = useForm();

  // Fetch groups on component mount
  useState(() => {
    const fetchGroups = async () => {
      try {
        const response = await api.get('/groups');
        setGroups(response.data);
      } catch (error) {
        console.error('Error fetching groups:', error);
      }
    };
    fetchGroups();
  }, []);

  const steps = [
    { id: 1, name: 'Personal Info', icon: User },
    { id: 2, name: 'Photo Capture', icon: Camera },
    { id: 3, name: 'Academic Info', icon: Users },
    { id: 4, name: 'Review', icon: Check },
  ];

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current.getScreenshot();
    setCapturedImage(imageSrc);
    setIsCapturing(false);
  }, [webcamRef]);

  const retakePhoto = () => {
    setCapturedImage(null);
    setIsCapturing(true);
  };

  const onSubmit = async (data) => {
    try {
      // Prepare form data with captured image
      const formData = new FormData();
      Object.keys(data).forEach(key => {
        formData.append(key, data[key]);
      });

      if (capturedImage) {
        // Convert base64 to blob
        const response = await fetch(capturedImage);
        const blob = await response.blob();
        formData.append('photo', blob, 'capture.jpg');
      }

      // Submit enrollment
      await api.post('/students/enroll', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      // Navigate back to students list
      navigate('/admin/students');
    } catch (error) {
      console.error('Error enrolling student:', error);
    }
  };

  const nextStep = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const formData = watch();

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Enroll New Student</h1>
        <p className="text-gray-600">Complete all steps to enroll a new student</p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <nav aria-label="Progress">
          <ol className="flex items-center">
            {steps.map((step, stepIdx) => (
              <li
                key={step.name}
                className={`${
                  stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''
                } relative`}
              >
                {currentStep > step.id ? (
                  <>
                    <div className="absolute inset-0 flex items-center" aria-hidden="true">
                      <div className="h-0.5 w-full bg-blue-600" />
                    </div>
                    <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 hover:bg-blue-700">
                      <Check className="h-5 w-5 text-white" />
                    </div>
                  </>
                ) : currentStep === step.id ? (
                  <>
                    {stepIdx !== 0 && (
                      <div className="absolute inset-0 flex items-center" aria-hidden="true">
                        <div className="h-0.5 w-full bg-gray-200" />
                      </div>
                    )}
                    <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-blue-600 bg-white">
                      <step.icon className="h-5 w-5 text-blue-600" />
                    </div>
                  </>
                ) : (
                  <>
                    {stepIdx !== 0 && (
                      <div className="absolute inset-0 flex items-center" aria-hidden="true">
                        <div className="h-0.5 w-full bg-gray-200" />
                      </div>
                    )}
                    <div className="relative flex h-8 w-8 items-center justify-center rounded-full border-2 border-gray-300 bg-white">
                      <step.icon className="h-5 w-5 text-gray-500" />
                    </div>
                  </>
                )}
                <span className="mt-2 block text-xs font-medium text-gray-900">
                  {step.name}
                </span>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-lg shadow p-6">
        {/* Step 1: Personal Information */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Personal Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Full Name *
                </label>
                <input
                  type="text"
                  {...register('name', { required: 'Name is required' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Student ID *
                </label>
                <input
                  type="text"
                  {...register('studentId', { required: 'Student ID is required' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
                {errors.studentId && (
                  <p className="mt-1 text-sm text-red-600">{errors.studentId.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Email *
                </label>
                <input
                  type="email"
                  {...register('email', {
                    required: 'Email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address',
                    },
                  })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Phone Number
                </label>
                <input
                  type="tel"
                  {...register('phone')}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Date of Birth
                </label>
                <input
                  type="date"
                  {...register('dateOfBirth')}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Address
                </label>
                <textarea
                  {...register('address')}
                  rows={3}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Photo Capture */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Capture Student Photo</h2>
            
            <div className="flex justify-center">
              {!capturedImage && !isCapturing && (
                <div className="text-center">
                  <div className="w-64 h-64 bg-gray-200 rounded-lg flex items-center justify-center">
                    <Camera className="h-16 w-16 text-gray-400" />
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsCapturing(true)}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                  >
                    Start Camera
                  </button>
                </div>
              )}

              {isCapturing && (
                <div className="text-center">
                  <Webcam
                    audio={false}
                    ref={webcamRef}
                    screenshotFormat="image/jpeg"
                    className="rounded-lg"
                    videoConstraints={{
                      width: 320,
                      height: 320,
                      facingMode: "user",
                    }}
                  />
                  <div className="mt-4 space-x-3">
                    <button
                      type="button"
                      onClick={capture}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                    >
                      Capture Photo
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsCapturing(false)}
                      className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {capturedImage && (
                <div className="text-center">
                  <img
                    src={capturedImage}
                    alt="Captured"
                    className="w-64 h-64 object-cover rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={retakePhoto}
                    className="mt-4 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 flex items-center mx-auto"
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Retake Photo
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Academic Information */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Academic Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Group/Class *
                </label>
                <select
                  {...register('groupId', { required: 'Group is required' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                  <option value="">Select a group</option>
                  {groups.map((group) => (
                    <option key={group.id} value={group.id}>
                      {group.name}
                    </option>
                  ))}
                </select>
                {errors.groupId && (
                  <p className="mt-1 text-sm text-red-600">{errors.groupId.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Enrollment Date *
                </label>
                <input
                  type="date"
                  {...register('enrollmentDate', { required: 'Enrollment date is required' })}
                  defaultValue={new Date().toISOString().split('T')[0]}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
                {errors.enrollmentDate && (
                  <p className="mt-1 text-sm text-red-600">{errors.enrollmentDate.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Academic Year
                </label>
                <input
                  type="text"
                  {...register('academicYear')}
                  placeholder="2024-2025"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Emergency Contact
                </label>
                <input
                  type="text"
                  {...register('emergencyContact')}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700">
                  Notes
                </label>
                <textarea
                  {...register('notes')}
                  rows={3}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Review Information</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Personal Information</h3>
                <dl className="space-y-2">
                  <div>
                    <dt className="text-sm text-gray-500">Name</dt>
                    <dd className="text-sm font-medium text-gray-900">{formData.name}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Student ID</dt>
                    <dd className="text-sm font-medium text-gray-900">{formData.studentId}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Email</dt>
                    <dd className="text-sm font-medium text-gray-900">{formData.email}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Phone</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formData.phone || 'Not provided'}
                    </dd>
                  </div>
                </dl>
              </div>

              <div>
                <h3 className="font-medium text-gray-900 mb-3">Academic Information</h3>
                <dl className="space-y-2">
                  <div>
                    <dt className="text-sm text-gray-500">Group</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {groups.find(g => g.id === formData.groupId)?.name || 'Not selected'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Enrollment Date</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formData.enrollmentDate}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-gray-500">Academic Year</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formData.academicYear || 'Not provided'}
                    </dd>
                  </div>
                </dl>
              </div>

              {capturedImage && (
                <div>
                  <h3 className="font-medium text-gray-900 mb-3">Photo</h3>
                  <img
                    src={capturedImage}
                    alt="Student"
                    className="w-32 h-32 object-cover rounded-lg"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="mt-8 flex justify-between">
          <button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 1}
            className={`flex items-center px-4 py-2 rounded-lg ${
              currentStep === 1
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Previous
          </button>

          {currentStep < steps.length ? (
            <button
              type="button"
              onClick={nextStep}
              className="flex items-center px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Next
              <ChevronRight className="h-4 w-4 ml-2" />
            </button>
          ) : (
            <button
              type="submit"
              className="flex items-center px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              <Check className="h-4 w-4 mr-2" />
              Complete Enrollment
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default EnrollStudent;
