export const dashboardPreviewStats = {
  overview: {
    total_users: 1284,
    active_users: 1169,
    total_detection_scenes: 14,
    total_detection_tasks: 3217,
    total_training_tasks: 86,
    total_food_items: 1248,
  },
  detection: {
    total: 3217,
    completed: 2974,
    failed: 188,
    pending: 37,
    processing: 18,
    total_objects_detected: 28653,
    avg_inference_time: 0.1847,
  },
  training: {
    total: 86,
    completed: 61,
    failed: 8,
    running: 4,
    pending: 8,
    paused: 5,
  },
  users: {
    total: 1284,
    active: 1169,
    superusers: 3,
    new_today: 24,
  },
}

export const emptyDashboardPreviewStats = {
  overview: {
    total_users: 0,
    active_users: 0,
    total_detection_scenes: 0,
    total_detection_tasks: 0,
    total_training_tasks: 0,
    total_food_items: 0,
  },
  detection: {
    total: 0,
    completed: 0,
    failed: 0,
    pending: 0,
    processing: 0,
    total_objects_detected: 0,
    avg_inference_time: null,
  },
  training: {
    total: 0,
    completed: 0,
    failed: 0,
    running: 0,
    pending: 0,
    paused: 0,
  },
  users: {
    total: 0,
    active: 0,
    superusers: 0,
    new_today: 0,
  },
}
