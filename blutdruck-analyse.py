# Initial imports and data loading
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

data = pd.read_csv('/mnt/data/blutdruck.csv')
heart_rate_data = data[data['type'] == "HKQuantityTypeIdentifierHeartRate"]

data_systolic = data[data['type'] == "HKQuantityTypeIdentifierBloodPressureSystolic"].rename(columns={"value": "value_systolic", "type": "type_systolic", "sourceName": "sourceName_systolic", "endDate": "endDate_systolic", "creationDate": "creationDate_systolic"})
data_diastolic = data[data['type'] == "HKQuantityTypeIdentifierBloodPressureDiastolic"].rename(columns={"value": "value_diastolic", "type": "type_diastolic", "sourceName": "sourceName_diastolic", "endDate": "endDate_diastolic", "creationDate": "creationDate_diastolic"})

merged_data = pd.merge_asof(data_systolic.sort_values('startDate'), data_diastolic.sort_values('startDate'), on="startDate", direction="nearest")

# Data splitting by year
data_2015_2016 = merged_data[(merged_data['startDate'].dt.year == 2015) | (merged_data['startDate'].dt.year == 2016)]
data_2019 = merged_data[merged_data['startDate'].dt.year == 2019]
data_2023 = merged_data[merged_data['startDate'].dt.year == 2023]

# Function to plot the data and trend
def plot_data_with_trend(data, title=''):
    fig, ax1 = plt.subplots(figsize=(15, 7))
    ax1.scatter(data['startDate'], data['value_systolic'], label='Systolic', color='b', marker='o')
    ax1.scatter(data['startDate'], data['value_diastolic'], label='Diastolic', color='r', marker='o')
    z_systolic = np.polyfit(data.index, data['value_systolic'], 1)
    p_systolic = np.poly1d(z_systolic)
    ax1.plot(data['startDate'], p_systolic(data.index), linestyle='-', color='b', alpha=0.5)
    z_diastolic = np.polyfit(data.index, data['value_diastolic'], 1)


    p_diastolic = np.poly1d(z_diastolic)
    ax1.plot(data['startDate'], p_diastolic(data.index), linestyle='-', color='r', alpha=0.5)
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Blood Pressure (mmHg)')
    ax1.set_title(title)
    ax1.legend(loc='upper left')

    heart_rate_filtered = heart_rate_data[(heart_rate_data['startDate'] >= data['startDate'].min()) &
                                          (heart_rate_data['startDate'] <= data['startDate'].max())]
    ax2 = ax1.twinx()
    ax2.scatter(heart_rate_filtered['startDate'], heart_rate_filtered['value'], label='Heart Rate', color='g', marker='x')
    ax2.set_ylabel('Heart Rate (count/min)')
    ax2.legend(loc='upper right')
    plt.tight_layout()
    plt.show()

# Average blood pressure calculation
average_systolic = merged_data['value_systolic'].mean()
average_diastolic = merged_data['value_diastolic'].mean()

# Function to filter out weeks with no recorded values
def filter_weeks_with_data(data):
    data['week'] = data['startDate'].dt.isocalendar().week
    data['year'] = data['startDate'].dt.year
    valid_weeks = data.groupby(['year', 'week']).filter(lambda x: len(x) > 0)
    return valid_weeks

# Function to plot data with German labels and adjusted x-axis limits
def plot_data_with_german_labels_adjusted(data, title):
    fig, ax1 = plt.subplots(figsize=(15, 7))
    ax1.scatter(data['startDate'], data['value_systolic'], label='Systolisch', color='b', marker='o')
    ax1.scatter(data['startDate'], data['value_diastolic'], label='Diastolisch', color='r', marker='o')
    z_systolic = np.polyfit(data.index, data['value_systolic'], 1)
    p_systolic = np.poly1d(z_systolic)
    ax1.plot(data['startDate'], p_systolic(data.index), linestyle='-', color='b', alpha=0.5)
    z_diastolic = np.polyfit(data.index, data['value_diastolic'], 1)
    p_diastolic = np.poly1d(z_diastolic)
    ax1.plot(data['startDate'], p_diastolic(data.index), linestyle='-', color='r', alpha=0.5)
    ax1.set_xlabel('Datum')
    ax1.set_ylabel('Blutdruck (mmHg)')
    ax1.set_title(title)
    ax1.legend(loc='upper left')
    ax1.set_xlim([data['startDate'].min(), data['startDate'].max()])
    heart_rate_filtered = heart_rate_data[(heart_rate_data['startDate'] >= data['startDate'].min()) &
                                          (heart_rate_data['startDate'] <= data['startDate'].max())]
    ax2 = ax1.twinx()
    ax2.scatter(heart_rate_filtered['startDate'], heart_rate_filtered['value'], label='Herzfrequenz', color='g', marker='x')
    ax2.set_ylabel('Herzfrequenz (Schläge/Min)')
    ax2.legend(loc='upper right')
    plt.tight_layout()
    plt.show()



# Extracting week and year from the startDate for boxplot
merged_data['week'] = merged_data['startDate'].dt.isocalendar().week
merged_data['year'] = merged_data['startDate'].dt.year

# Relevant data filtering for 2015 + 2016, 2019, and 2023
relevant_data = merged_data[merged_data['year'].isin([2015, 2016, 2019, 2023])]

# Plotting the boxplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)

# Boxplot for Systolic Blood Pressure
relevant_data.boxplot(column='value_systolic', by=['year', 'week'], ax=ax1, grid=False)
ax1.set_title('Boxplot für Systolischen Blutdruck')
ax1.set_ylabel('Systolischer Blutdruck (mmHg)')
ax1.set_xlabel('')

# Boxplot for Diastolic Blood Pressure
relevant_data.boxplot(column='value_diastolic', by=['year', 'week'], ax=ax2, grid=False)
ax2.set_title('Boxplot für Diastolischen Blutdruck')
ax2.set_ylabel('Diastolischer Blutdruck (mmHg)')
ax2.set_xlabel('Jahr, Woche')

# Adjusting layout
fig.suptitle('')
plt.tight_layout()
plt.xticks(rotation=90)
plt.show()

