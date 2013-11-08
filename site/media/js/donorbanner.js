$(document).ready(function() {

    var STATE_OPEN = 0,
        STATE_COLLAPSED = 1,
        STATE_DISMISSED = 2;

    var Banner = function(container) {
        var that = this;
        this.$container = $(container);
        this.$toggleButton = $('#donor_banner .toggleButton');
        this.state = null;

        this.$toggleButton.click(function() {
            switch (that.state) {
                case STATE_OPEN:
                    that.collapse();
                    break;
                case STATE_COLLAPSED:
                    that.dismiss();
                    break;
            }
            that.saveState();
        });

        this.loadState();
    };

    Banner.prototype.open = function() {
        this.$container.addClass("revealbanner");
        this.$toggleButton.text("Not now");
        this.state = STATE_OPEN;
    };

    Banner.prototype.collapse = function() {
        this.$container.addClass("revealbanner").addClass("collapsed");
        this.$toggleButton.text("Close");
        this.state = STATE_COLLAPSED;
    };

    Banner.prototype.dismiss = function() {
        this.$container.removeClass("revealbanner").removeClass('collapsed');
        this.state = STATE_DISMISSED;
    };

    Banner.prototype.saveState = function() {
        if (window.localStorage) {
            localStorage.setItem("donorbanner-state", this.state);
        }
    };

    Banner.prototype.loadState = function() {

        var newState = STATE_OPEN;

        if (window.localStorage) {
            var storedState = localStorage.getItem("donorbanner-state");
            if (storedState !== null) {
                newState = parseInt(storedState, 10);
            }
        } else {
            newState = STATE_COLLAPSED;
        }

        if (newState != this.state) {
            if (newState == STATE_OPEN) {
                this.open();
            } else if (newState == STATE_COLLAPSED) {
                this.collapse();
            } else if (newState == STATE_DISMISSED) {
                this.dismiss();
            }
            this.state = newState;
        }
    };

    var banner = new Banner($('html'));

});