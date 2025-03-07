import savemappedcomponents
import retrain
import savemappedcomponents
import saveunmappedcomponents
import app
import gui

if __name__ == '__main__':
    savemappedcomponents.export_training_data()
    retrain.retrain()
    saveunmappedcomponents.process_computers_from_date("2025-03-06")
    app.app.run(debug=True)
    gui.run_ui()



