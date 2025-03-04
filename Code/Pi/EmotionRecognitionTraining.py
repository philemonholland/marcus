import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.optimizers.schedules import ExponentialDecay
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import cv2
import numpy as np
from tensorflow.keras.models import load_model


# Check if GPU is available
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        # Set memory growth to avoid TensorFlow reserving all GPU memory
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"Using GPU: {gpus}")
    except RuntimeError as e:
        print(e)
else:
    print("GPU not found. Running on CPU.")

# Define paths
data_dir = ".\\fer2013"

# Dataset configuration
batch_size = 64*2
img_height = 48
img_width = 48

# Data augmentation using ImageDataGenerator
train_datagen = ImageDataGenerator(
    rescale=1.0 / 255,
    rotation_range=30,
    width_shift_range=0.2,
    height_shift_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest',
    validation_split=0.2
)

val_datagen = ImageDataGenerator(rescale=1.0 / 255, validation_split=0.2)

# Apply the image generators
train_generator = train_datagen.flow_from_directory(
    data_dir,
    subset="training",
    seed=123,
    batch_size=batch_size,
    color_mode="grayscale",
    target_size=(img_height, img_width),
    class_mode='sparse'
)

val_generator = val_datagen.flow_from_directory(
    data_dir,
    subset="validation",
    seed=123,
    batch_size=batch_size,
    color_mode="grayscale",
    target_size=(img_height, img_width),
    class_mode='sparse'
)

# Model architecture with Batch Normalization
model = models.Sequential([
    layers.Conv2D(64, (3, 3), activation='relu', input_shape=(48, 48, 1)),
    layers.BatchNormalization(),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),
    
    layers.Conv2D(128, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.Conv2D(128, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),
    
    layers.Conv2D(256, (3, 3), activation='relu'),
    layers.BatchNormalization(),
    layers.MaxPooling2D((2, 2)),

    layers.Flatten(),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.5),
    layers.BatchNormalization(),
    layers.Dense(7, activation='softmax')
])

# Define a learning rate schedule
lr_schedule = ExponentialDecay(
    initial_learning_rate=0.001, # Lower to avoid overshooting
    decay_steps=5000,            # Slow decay
    decay_rate=0.95               # Slower decay for more fine-tuning
)



# Compile the model
optimizer = Adam(learning_rate=lr_schedule)
model.compile(optimizer=optimizer,
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

model.summary()

# Train the model with the data generator
history = model.fit(
    train_generator,
    validation_data=val_generator,
    epochs=50
)

# Save the model
model.save('emotion_recognition_model.h5')

# Evaluate the model on the validation set
test_loss, test_accuracy = model.evaluate(val_generator)
print(f"Validation accuracy: {test_accuracy:.2f}")


cap.release()
cv2.destroyAllWindows()
