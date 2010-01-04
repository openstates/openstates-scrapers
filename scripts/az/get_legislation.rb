#!/usr/bin/env ruby
require File.join(File.dirname(__FILE__), '..', 'rbutils', 'new_legislation')
require 'hpricot'
require 'open-uri'

class ArizonaScraper < LegislationScraper
  @@state = "az"
  
  def get_bills(uri, prefix)
    doc = Hpricot(open(uri))
    (doc/"table.ContentAreaBackground table tr").map do |row|
      bill_id = (row/"td").first.inner_text.strip
      bill_id if bill_id =~ /^#{prefix}/
    end.compact
  end
  def parse_bill(bill_id)
    uri = "http://www.azleg.gov/FormatDocument.asp?inDoc=/legtext/49leg/1r/bills/#{bill_id}o.asp"
    doc = Hpricot(open(uri))
    rv = {}
    (doc/"table.ContentAreaBackground td table").each do |x|
      key_vals = (x/"td")

      key = key_vals[0].inner_text.strip.downcase
      key = key[0..key.length-2]
      
      if key == "sponsors"
        
        sponsors = []
        (x/"tr").each do |r|
          sponsor = {}
          sponsor_set = (r/"td")
          sponsor_set.delete_at(0) # get rid of the sponsor key

          sponsor_set.each_with_index do |d, i|
            if i % 2 == 0
              sponsor["sponsor"] = d.inner_text.strip.capitalize
            else
              sponsor["type"] = d.inner_text.strip=='P' ? 'primary' : 'co-sponsor'
              sponsors << sponsor
              sponsor = {}
            end
          end
        end

        rv[key] = sponsors
      elsif key == "title"
        val = key_vals[1].inner_text.strip
        rv[key] = val
      end
      # puts " Found [#{key}] with #{key_vals.size}. Data: [#{val}]"
      rv["url"] = uri
    end
    rv
  end
  
  def scrape_bills(chamber, session)
    params = chamber=="lower" ? ["allhouse","HB"] : ["allsenate","SB"]
    
    bill_list = get_bills("http://www.azleg.gov/Bills.asp?view=#{params[0]}",params[1])
    
    bill_list.each do |bill_id|
      bill_hash = parse_bill(bill_id)
      bill = Bill.new('49leg', chamber, bill_id, bill_hash['title'])
      bill_hash['sponsors'].each { |s| bill.add_sponsor(s['type'] || 'primary', s['sponsor']) }
      add_bill bill
      #puts "added bill: #{bill_id}"
    end

  end

  def scrape_legislators(chamber, session)
    leg = Legislator.new("Session 1", "upper", "1st District", "Bill Smith",
                         "Bill", "Smith", "", "Republican")
    self.add_legislator leg
  end

  def scrape_metadata
    {:state_name => "Arizona",
      :legislature_name => "Arizona Legislature",
      :upper_chamber_name => "Senate",
      :lower_chamber_name => "House of Representatives",
      :upper_term => 2,
      :lower_term => 2,
      :sessions => ["Forty-ninth Legislature"],
      :session_details => {"Forty-ninth Legislature" =>
        {:years => [2009, 2010],
          :sub_sessions => ["Forty-ninth Legislature - First Regular Session"]}
      }}
  end
end

ArizonaScraper.new.run
