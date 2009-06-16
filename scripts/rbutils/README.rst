================
Ruby Scraper API
================

An implementation of the older, CSV based format exists in `legislation.rb` for backwards compatibility. New scrapers should target the API in `new_legislation.rb`.

Scrapers should subclass ``LegislationScraper``, overriding ``scrape_metadata``, ``scrape_legislators`` and ``scrape_bills`` and setting the ``@@state`` class variable to the state's two-letter abbreviation.

A call to ``scrape_metadata`` should return a ``Hash`` containing the fields documented in :ref:`metadata-label`.

A call to ``scrape_legislators`` should grab all of the legislators serving in the requested chamber/session. For each legislator, the scraper should create a ``Legislator`` object and pass it to ``add_legislator``.

A call to ``scrape_bills`` should grab all of the bills for the requested chamber/session. For each bill, the scraper should create a ``Bill`` object and pass it to ``add_bill``.

The Ruby API is closely modeled after the Python API, see the documentation of the :doc:`Python API <../pyutils/README>` if anything is unclear.

An example of the Ruby scraping API (that doesn't actually scrape anything):

.. code-block:: ruby

  #!/usr/bin/env ruby
  require File.join(File.dirname(__FILE__), '..', 'rbutils', 'new_legislation')

  class ExampleScraper < LegislationScraper
    @@state = "ex"
  
    def scrape_bills(chamber, session)
      bill = Bill.new("Session 1", "upper", "SB 1", "The First Bill")
      bill.add_sponsor("primary", "Bill Smith")
      bill.add_sponsor("cosponsor", "John Doe")
      bill.add_action("upper", "Introduced", "12/01/09")
      bill.add_version("first version", "http://example.org")
    
      vote = Vote.new("upper", "12/02/09", "Pass", true,
                      10, 3, 1)
      vote.yes "Bill Smith"
      vote.no "John Doe"
    
      bill.add_vote vote
      self.add_bill bill
    end
  
    def scrape_legislators(chamber, session)
      leg = Legislator.new("Session 1", "upper", "1st District", "Bill Smith",
                           "Bill", "Smith", "", "Republican")
      self.add_legislator leg
    end
  
    def scrape_metadata
      {:state_name => "Example State",
        :legislature_name => "Example State Assembly",
        :upper_chamber_name => "Senate",
        :lower_chamber_name => "House of Representatives",
        :upper_term => 4,
        :lower_term => 2,
        :sessions => ["Session 1", "Session 2"],
        :session_details => {"Session 1" =>
          {:years => [2005, 2006],
            :sub_sessions => ["Session 1 Part 2"]},
          "Session 2" =>
          {:years => [2007, 2008],
            :sub_sessions => []}}}
    end
  end

  ExampleScraper.new.run
