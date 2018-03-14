correlator_ui.py: correlator.ui
	pyuic5 $< > $@

clean:
	rm correlator_ui.py
