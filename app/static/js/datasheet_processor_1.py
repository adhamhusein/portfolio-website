# Data Processing Pipeline for Vehicle Movement Analysis

import pandas as pd
import numpy as np

class VehicleDataProcessor:
    # Handles processing of vehicle movement data
    def __init__(self, input_file: str, output_file: str):
        self.input_file = input_file
        self.output_file = output_file
        self.df = None
        self.df_processed = None

    def load_data(self):
        # Load and sort the input data by mobileid and reporttime
        self.df = pd.read_csv(self.input_file)
        self.df_processed = self.df.sort_values(['mobileid', 'reporttime']).copy()
        return self.df_processed

    def calculate_vessel_angle(self):
        # Set vessel_angle to -50 if mobileactivityid is 8, else 0; override to 0 if speed > 5
        if 'mobileactivityid' in self.df_processed.columns:
            self.df_processed['vessel_angle'] = np.where(
                self.df_processed['mobileactivityid'] == 8, -50, 0
            )
            if 'pos_speed' in self.df_processed.columns:
                self.df_processed.loc[self.df_processed['pos_speed'] > 5, 'vessel_angle'] = 0
        else:
            self.df_processed['vessel_angle'] = 0

    def fix_plm_payload_zeros(self):
        # Replace plm_payload values of 0 with 0.1
        if 'plm_payload' in self.df_processed.columns:
            self.df_processed['plm_payload'] = self.df_processed['plm_payload'].replace(0, 0.1)

    def fix_stationary_positions(self):
        # Set pos_dir to 0 when position doesn't change between consecutive records
        def set_pos_dir_zero_if_same_lon_lat(group):
            same_next = (
                (group['pos_lon'] == group['pos_lon'].shift(-1)) &
                (group['pos_lat'] == group['pos_lat'].shift(-1))
            )
            group.loc[same_next, 'pos_dir'] = 0
            return group
        self.df_processed = self.df_processed.groupby('mobileid', group_keys=False).apply(set_pos_dir_zero_if_same_lon_lat)

    def fill_missing_directions(self):
        # Fill missing pos_dir values using forward and backward fill
        self.df_processed['pos_dir'] = self.df_processed.groupby('mobileid')['pos_dir'].transform(
            lambda x: x.replace(0, method='ffill')
        )
        def fill_leading_zeros_with_first_nonzero(x):
            if x.iloc[0] == 0:
                x = x.replace(0, method='bfill')
            return x
        self.df_processed['pos_dir'] = self.df_processed.groupby('mobileid')['pos_dir'].transform(
            fill_leading_zeros_with_first_nonzero
        )

    def calculate_direction_gaps(self):
        # Calculate direction gaps between consecutive positions
        def calculate_dir_gap(group):
            current_pos_dir = group['pos_dir']
            next_pos_dir = group['pos_dir'].shift(-1)
            abs_diff = abs(current_pos_dir - next_pos_dir)
            mod_360 = abs_diff % 360
            dir_gap = np.minimum(mod_360, 360 - mod_360)
            dir_gap.iloc[-1] = np.nan
            return dir_gap
        self.df_processed['dir_gap'] = self.df_processed.groupby('mobileid').apply(
            calculate_dir_gap
        ).reset_index(level=0, drop=True)

    def identify_reversed_movements(self):
        # Identify reversed movements based on direction gaps
        def calculate_is_reversed(group):
            is_reversed = []
            toggle = 0
            toggle_next = False
            for _, row in group.iterrows():
                if toggle_next:
                    toggle = 1 - toggle
                    toggle_next = False
                if row.get('dir_gap', 0) > 90:
                    toggle_next = True
                is_reversed.append(toggle)
            return pd.Series(is_reversed, index=group.index)
        self.df_processed['is_reversed'] = self.df_processed.groupby('mobileid').apply(
            calculate_is_reversed
        ).reset_index(level=0, drop=True)

    def calculate_sequence_statistics(self):
        # Calculate average speed and data count for each movement sequence
        def assign_avg_speed_and_count(group):
            seq_id = (group['is_reversed'] != group['is_reversed'].shift()).cumsum()
            def mean_speed_above_1(x):
                filtered = x[x > 1]
                return filtered.mean() if not filtered.empty else np.nan
            avg_speed = group.groupby(seq_id)['pos_speed'].transform(mean_speed_above_1)
            n_data_seq = group.groupby(seq_id)['pos_speed'].transform('count')
            return pd.DataFrame({'avg_speed': avg_speed, 'n_data_seq': n_data_seq}, index=group.index)
        seq_stats = self.df_processed.groupby('mobileid', group_keys=False).apply(assign_avg_speed_and_count)
        self.df_processed['avg_speed'] = seq_stats['avg_speed']
        self.df_processed['n_data_seq'] = seq_stats['n_data_seq']

    def apply_speed_corrections(self):
        # Set is_reversed to 0 for high speed and long sequences
        high_speed_mask = (self.df_processed['avg_speed'] > 10) & (self.df_processed['n_data_seq'] > 10)
        self.df_processed.loc[high_speed_mask, 'is_reversed'] = 0

    def add_plm_state(self):
        # Add 'plm_state' column: 'plm off' if abs(pos_speed - plm_speed) > 5, else 'plm on'
        if 'pos_speed' in self.df_processed.columns and 'plm_speed' in self.df_processed.columns:
            diff = abs(self.df_processed['pos_speed'] - self.df_processed['plm_speed'])
            self.df_processed['plm_state'] = np.where(diff > 5, 'plm off', 'plm on')
        else:
            self.df_processed['plm_state'] = 'unknown'

    def add_8_hours_to_reporttime(self):
        # Add 8 hours to the 'reporttime' column if it exists
        if 'reporttime' in self.df_processed.columns:
            # Try to parse as datetime, add 8 hours, and format back to string if needed
            self.df_processed['reporttime'] = pd.to_datetime(self.df_processed['reporttime']) + pd.Timedelta(hours=8)
            # If original was string, convert back to string in the same format
            if self.df['reporttime'].dtype == object:
                self.df_processed['reporttime'] = self.df_processed['reporttime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    def export_results(self):
        # Export only the specified columns to CSV file in the given order
        columns_to_export = [
            'mobileid', 'reporttime', 'mobiletypeid', 'mobileactivityid', 'mobilestatusid',
            'pos_lon', 'pos_lat', 'pos_alt', 'pos_speed', 'pos_dir',
            'plm_payload', 'plm_inc', 'plm_status', 'is_reversed',
            'vessel_angle', 'plm_state'
        ]
        columns_to_export = [col for col in columns_to_export if col in self.df_processed.columns]
        self.df_processed[columns_to_export].to_csv(self.output_file, index=False)

    def process(self):
        # Execute the complete data processing pipeline
        self.load_data()
        self.fix_plm_payload_zeros()
        self.fix_stationary_positions()
        self.fill_missing_directions()
        self.calculate_direction_gaps()
        self.identify_reversed_movements()
        self.calculate_sequence_statistics()
        self.apply_speed_corrections()
        self.calculate_vessel_angle()
        self.add_plm_state()
        self.add_8_hours_to_reporttime()
        self.export_results()
        return self.df_processed