import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, RepeatVector, TimeDistributed

class LSTMAutoencoder:
    def __init__(self, sequence_length=30, epochs=20, batch_size=16):
        """
        Initializes the LSTM Autoencoder model.
        Args:
            sequence_length (int): The number of time steps in each sequence.
            epochs (int): The number of training epochs.
            batch_size (int): The batch size for training.
        """
        self.sequence_length = sequence_length
        self.epochs = epochs
        self.batch_size = batch_size
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None
        self.training_mae_loss = None

    def _create_sequences(self, values):
        """
        Converts a 1D array of values into a 3D array of overlapping sequences.
        """
        output = []
        for i in range(len(values) - self.sequence_length + 1):
            output.append(values[i : (i + self.sequence_length)])
        return np.stack(output)

    def build_model(self, n_features):
        """
        Defines the architecture of the LSTM autoencoder.
        """
        self.model = Sequential()
        # Encoder
        self.model.add(LSTM(128, activation='relu', input_shape=(self.sequence_length, n_features)))
        self.model.add(RepeatVector(self.sequence_length))
        # Decoder
        self.model.add(LSTM(128, activation='relu', return_sequences=True))
        self.model.add(TimeDistributed(Dense(n_features)))
        
        self.model.compile(optimizer='adam', loss='mae')
        print("LSTM Autoencoder model built successfully.")
        self.model.summary()

    def train(self, df_train):
        """
        Trains the autoencoder on a DataFrame of normal operational data.
        """
        print("Training LSTM Autoencoder...")
        # Scale the training data
        scaled_data = self.scaler.fit_transform(df_train[['EngineLoad']])
        
        # Create sequences from the scaled data
        sequences = self._create_sequences(scaled_data)
        n_features = sequences.shape[2]
        
        # Build the model
        self.build_model(n_features)
        
        # Train the model
        history = self.model.fit(
            sequences, sequences,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.1,
            shuffle=False,
            verbose=1
        )
        
        # Store the training loss to help determine the anomaly threshold
        self.training_mae_loss = np.mean(history.history['loss'])
        print(f"Training complete. Average MAE loss: {self.training_mae_loss}")

    def predict(self, df_sequence):
        """
        Calculates the reconstruction error for a new data sequence.
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained yet. Call train() first.")
        
        # Scale the new sequence
        scaled_sequence = self.scaler.transform(df_sequence[['EngineLoad']])
        
        # Reshape into a single sequence for prediction
        sequence = np.asarray(scaled_sequence).astype('float32').reshape(1, self.sequence_length, 1)
        
        # Get the model's prediction
        reconstructed_sequence = self.model.predict(sequence)
        
        # Calculate the Mean Absolute Error (reconstruction error)
        mae_loss = np.mean(np.abs(reconstructed_sequence - sequence))
        
        return mae_loss