/**
 * livePositions namespace.
 */
var livePositions = (function(global, $) {
    var LivePositionsController = klass(function(params) {
        // initilize params.
        this._livePositionsStreamURL = params.livePositionsStreamURL;
        this._livePositionsStateURL = params.livePositionsStateURL;

        // set everything up.
        this._setupSSE();
        this._setupUIListeners();

        // show the current state.
        this._loadCurrentLivePositionsState();
    }).methods({
        /**
         * Setup the event stream for live positions.
         * If EventSource unavailable, fallback to xHR pooling.
         */
        _setupSSE: function() {
            // check if this browser has SSE capability.
            if (global.EventSource) {
                var eventSource = new EventSource(this._livePositionsStreamURL);

                eventSource.addEventListener("positions", function(e) {
                    $("#live_positions_state").html(e.data);
                });
            }
            else {
                this._setupSSEFallback();
            }
        },

        /**
         * Setup a simple fallback for the SSE capability using a xHR pooling.
         */
        _setupSSEFallback: function() {
            setTimeout(_loadCurrentLivePositionsState, 2000);
        },

        /**
         * Setup UI listeners
         */
        _setupUIListeners: function() {
            var _self = this;
           
        },

        /**
         * Load the current live positions state by performing an ajax call.
         */
        _loadCurrentLivePositionsState: function() {
            $("#live_positions_state").load(this._livePositionsStateURL);
        }
    });

    return {
        LivePositionsController: LivePositionsController
    };
})(window, jQuery);