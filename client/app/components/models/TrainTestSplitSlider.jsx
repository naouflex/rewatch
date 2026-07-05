import React from "react";
import PropTypes from "prop-types";
import Slider from "antd/lib/slider";
import moment from "moment";

import "./TrainTestSplitSlider.less";

class TrainTestSplitSlider extends React.Component {
  constructor(props) {
    super(props);
    this.sliderRef = React.createRef();
  }

  componentDidMount() {
    if (this.sliderRef.current) {
      this.sliderRef.current.addEventListener("wheel", this.handleScroll);
    }
  }

  componentWillUnmount() {
    if (this.sliderRef.current) {
      this.sliderRef.current.removeEventListener("wheel", this.handleScroll);
    }
  }

  handleScroll = event => {
    if (!this.props.editMode) {
      return; // Prevent scrolling if in disabled mode
    }
    
    event.preventDefault();
    const { step, min, max, trainSize } = this.props;
    const delta = event.deltaY > 0 ? -step : step; // Scrolling up increases, scrolling down decreases

    let newTrainSize = trainSize + delta;
    if (newTrainSize < min) newTrainSize = min;
    if (newTrainSize > max) newTrainSize = max;

    // Round to 2 decimal places
    newTrainSize = parseFloat(newTrainSize.toFixed(2));

    this.props.onTrainSizeChange(newTrainSize);
  };

  handleSliderChange = value => {
    // Round value to 2 decimal places
    const roundedValue = parseFloat(value.toFixed(2));
    this.props.onTrainSizeChange(roundedValue); // Call the callback function
  };

  formatDate(date) {
    // Check if the date is a Unix timestamp (number)
    if (!isNaN(date) && typeof date !== 'object') {
      // Determine if timestamp is in seconds (10 digits) or milliseconds (13 digits)
      const timestamp = date.toString().length <= 10 ? date * 1000 : date;
      return moment(timestamp).format('YYYY-MM-DD');
    }
    return moment(date).format('YYYY-MM-DD');
  }

  render() {
    const { trainSize, editMode, timestampData } = this.props; 

    // Calculate dates if timestamp data is available
    let firstDate = null;
    let lastDate = null;
    let cutoffDate = null;

    if (timestampData && timestampData.dates && timestampData.dates.length > 0) {
      // Sort dates to ensure they're in chronological order
      const sortedDates = [...timestampData.dates].sort((a, b) => {
        // Handle Unix timestamps (numbers) or string dates
        const dateA = !isNaN(a) && typeof a !== 'object' 
          ? (a.toString().length <= 10 ? a * 1000 : a) 
          : new Date(a);
        const dateB = !isNaN(b) && typeof b !== 'object'
          ? (b.toString().length <= 10 ? b * 1000 : b)
          : new Date(b);
        
        return dateA - dateB;
      });
      
      firstDate = sortedDates[0];
      lastDate = sortedDates[sortedDates.length - 1];
      
      // Calculate the cutoff date based on trainSize
      const index = Math.floor(sortedDates.length * trainSize) - 1;
      cutoffDate = index >= 0 ? sortedDates[index] : firstDate;
    }

    return (
      <div className="train-test-split-slider" ref={this.sliderRef}>
        <div className="labels">
          <div className="train-label" style={{ width: `${trainSize * 100}%`, textAlign: "center" }}>
            Train Data: {`${(trainSize * 100).toFixed(0)}%`}
          </div>
          <div className="test-label" style={{ width: `${(1 - trainSize) * 100}%`, textAlign: "center" }}>
            Test Data: {`${((1 - trainSize) * 100).toFixed(0)}%`}
          </div>
        </div>

        {/* Date display row */}
        {firstDate && lastDate && (
          <div className="date-labels">
            <div className="date-first">{this.formatDate(firstDate)}</div>
            <div className="date-cutoff" style={{ left: `${trainSize * 100}%` }}>
              {this.formatDate(cutoffDate)}
            </div>
            <div className="date-last">{this.formatDate(lastDate)}</div>
          </div>
        )}

        <div className="brackets">
          <div className="train-bracket" style={{ width: `${trainSize * 100}%` }} />
          <div className="test-bracket" style={{ width: `${(1 - trainSize) * 100}%` }} />
        </div>

        <Slider
          min={0}
          max={1}
          step={0.01}
          value={trainSize}
          onChange={this.handleSliderChange}
          marks={{
            0: "0%",
            0.25: "25%",
            0.5: "50%",
            0.75: "75%",
            1: "100%",
          }}
          tooltipVisible={false}
          disabled={!editMode}
        />
      </div>
    );
  }
}

TrainTestSplitSlider.propTypes = {
  trainSize: PropTypes.number.isRequired,
  onTrainSizeChange: PropTypes.func.isRequired,
  editMode: PropTypes.bool.isRequired,
  min: PropTypes.number,
  max: PropTypes.number,
  step: PropTypes.number,
  timestampData: PropTypes.shape({
    dates: PropTypes.arrayOf(PropTypes.string),
    column: PropTypes.string
  })
};

TrainTestSplitSlider.defaultProps = {
  min: 0.01,
  max: 1,
  step: 0.01,
  timestampData: null
};

export default TrainTestSplitSlider;
