export const trainingPreviewTasks = {
  data: {
    items: [
      {
        task_uuid: 'train-7f2c9a', model_name: 'yolo11s', status: 'running', progress: 64,
        data_yaml: '/datasets/uecfood256/data.yaml', epochs: 100, current_epoch: 64,
        img_size: 640, batch_size: 32, created_at: '2026-07-16T05:20:00Z', updated_at: '2026-07-16T08:42:00Z',
      },
      {
        task_uuid: 'train-5a4b1d', model_name: 'yolo11n', status: 'completed', progress: 100,
        data_yaml: '/datasets/food101/data.yaml', epochs: 80, current_epoch: 80,
        img_size: 640, batch_size: 48, created_at: '2026-07-14T02:15:00Z', completed_at: '2026-07-14T09:30:00Z',
      },
      {
        task_uuid: 'train-1d8e3f', model_name: 'yolo11m', status: 'paused', progress: 28,
        data_yaml: '/datasets/private/data.yaml', epochs: 120, current_epoch: 34,
        img_size: 768, batch_size: 16, created_at: '2026-07-13T03:05:00Z', updated_at: '2026-07-13T06:10:00Z',
      },
    ],
    total: 3,
    page: 1,
    page_size: 20,
  },
}

export const trainingPreviewStats = {
  data: { total: 86, completed: 61, failed: 8, running: 4, pending: 8, paused: 5 },
}

export const trainingPreviewModels = {
  data: {
    models: [
      { name: 'food-yolo11s-v3.pt', size_bytes: 42840000, created_at: '2026-07-14T09:30:00Z' },
      { name: 'food-yolo11n-v2.pt', size_bytes: 11820000, created_at: '2026-07-08T12:10:00Z' },
    ],
  },
}

export const trainingPreviewMetrics = {
  data: {
    task_uuid: 'train-5a4b1d',
    model_name: 'yolo11n',
    epochs: Array.from({ length: 16 }, (_, index) => {
      const epoch = (index + 1) * 5
      return {
        epoch,
        train_box_loss: 2.4 / (1 + index * .22),
        train_cls_loss: 4.8 / (1 + index * .28),
        val_box_loss: 2.2 / (1 + index * .2),
        val_cls_loss: 4.2 / (1 + index * .25),
        mAP50: Math.min(.78, .28 + index * .033),
        mAP50_95: Math.min(.61, .18 + index * .029),
        precision: Math.min(.74, .36 + index * .026),
        recall: Math.min(.70, .33 + index * .025),
      }
    }),
    final_metrics: { mAP50: .775, 'mAP50-95': .602, precision: .739, recall: .698 },
  },
}
